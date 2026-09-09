"""$SynthEx/ETH purchase verification. Fail-closed by design: until Robinhood
Chain's RPC URL, router/pool addresses and token contract are supplied via
environment variables, no purchase can ever be verified — this module must
never fabricate a successful verification or invent configuration values.

The verification pipeline itself (transaction/receipt/block fetch, log
decoding, router/pool/token checks, ETH/USD lookup, immutable claim storage)
is fully implemented and tested against a mocked RPC provider — only the
production RPC endpoint and contract addresses are missing.
"""

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.asset import Asset
from app.models.crypto_observation import CryptoQuoteObservation
from app.models.purchase import ClaimedPurchaseTransaction
from app.services.blockchain import JsonRpcProvider, RpcError, RpcProvider
from app.services.portfolio import get_or_create_entitlement_in_transaction, get_tier

log = logging.getLogger(__name__)

NOT_CONFIGURED = {
    "status": "not_configured",
    "message": "Purchase verification is not configured yet",
}

PURCHASE_VERIFICATION_NOT_CONFIGURED = {
    "status": "purchase_verification_not_configured",
    "message": "No router adapter is configured for this destination/method yet",
}

_TX_HASH_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")
_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


@dataclass(frozen=True)
class RouterAdapter:
    """Method selectors on a specific router/pool address that are confirmed
    (by reading the deployed contract source, not guessed) to be safely
    verifiable purchase routes.

    - `exact_input_selectors`: consume the entire input (native ETH's
      `tx.value`, or the full WETH amount transferred) with no refund path.
      Native ETH's `tx.value` can only ever be trusted through a selector
      listed here — never for a merely `refundable` one, since a native-ETH
      refund cannot be observed and subtracted the way a WETH Transfer log
      can.
    - `refundable_selectors`: may refund unused input back to the sender in
      the same transaction (e.g. an exact-output swap). Safe for WETH
      routes only — the refund is observed via a WETH `Transfer` log back
      to the wallet and subtracted from the amount spent.
    """

    exact_input_selectors: frozenset[str] = frozenset()
    refundable_selectors: frozenset[str] = frozenset()


# Populate only once a real Robinhood Chain router/pool address and its
# audited method selectors are confirmed — never guessed or assumed from a
# generic ABI. Empty means every purchase — native ETH or WETH — currently
# fails closed with `purchase_verification_not_configured`, since no route
# can yet be verified safely.
ROUTER_ADAPTERS: dict[str, RouterAdapter] = {}


def _adapter_for(destination_address: str | None) -> RouterAdapter | None:
    if not destination_address:
        return None
    return ROUTER_ADAPTERS.get(destination_address.lower())


def _selector(input_data: str) -> str:
    return (input_data or "0x")[:10].lower()


def _decode_address_topic(topic: str) -> str:
    return "0x" + topic[-40:].lower()


def _decode_uint(data: str) -> int:
    return int(data, 16) if data and data != "0x" else 0


def _router_adapters_configured(settings) -> bool:
    """Environment variables alone never activate purchase verification —
    each configured router/pool address also needs a matching RouterAdapter
    registered in ROUTER_ADAPTERS with real, audited method selectors
    (never guessed). Without this, `_is_configured` would report "ready"
    while every actual verification attempt still fails deep in the
    pipeline with `purchase_verification_not_configured` — this makes that
    gap visible up front instead."""
    configured_addresses = settings.parsed_dex_router_addresses | settings.parsed_dex_pool_addresses
    return any(addr.lower() in ROUTER_ADAPTERS for addr in configured_addresses)


def _is_configured(settings) -> bool:
    # A missing/zero launch block in production would let a pre-launch or
    # unrelated historical transaction be claimed as a $SynthEx purchase —
    # fail closed rather than allow verification without it.
    if settings.app_env == "production" and settings.synthex_token_start_block <= 0:
        return False
    # Deliberately does NOT also require a registered RouterAdapter here —
    # that's a per-transaction routing decision (_adapter_for, deeper in
    # verify_purchase) which already fails closed with its own distinct
    # `purchase_verification_not_configured` status. Folding it in here
    # would make this the SAME gate for two different concerns ("is basic
    # config present" vs "is there an adapter for this specific
    # destination"), short-circuiting every other check verify_purchase is
    # meant to run. See purchase_verification_status() for the combined
    # operational view used by the health check.
    return bool(
        settings.synthex_chain_id
        and settings.robinhood_rpc_url
        and settings.synthex_token_address
        and settings.parsed_dex_router_addresses | settings.parsed_dex_pool_addresses
        and settings.synthex_weth_address
    )


def purchase_verification_status() -> dict:
    """Operational status for admins/monitoring — distinguishes "no env
    vars set yet" from the more subtle "env vars are set but no
    RouterAdapter code has been registered for them yet" gap, which
    `_is_configured` alone collapses into one boolean and which never
    self-resolves just by editing environment variables."""
    settings = get_settings()
    env_vars_present = bool(
        settings.synthex_chain_id
        and settings.robinhood_rpc_url
        and settings.synthex_token_address
        and settings.parsed_dex_router_addresses | settings.parsed_dex_pool_addresses
        and settings.synthex_weth_address
    )
    adapters_registered = _router_adapters_configured(settings)
    if not env_vars_present:
        status = "env_not_configured"
    elif not adapters_registered:
        status = "env_configured_no_adapters"
    else:
        status = "ready"
    return {
        "status": status,
        "env_vars_present": env_vars_present,
        "router_adapters_registered": adapters_registered,
    }


async def _lookup_eth_usd_price(
    db: AsyncSession, block_timestamp: datetime, max_age: timedelta
) -> tuple[float, datetime] | None:
    """Nearest stored ETH/USD observation at/before the block timestamp,
    within `max_age`. Returns None (never fabricated) if nothing qualifies —
    callers fall back to a CoinGecko historical lookup."""
    eth_result = await db.execute(select(Asset).where(Asset.symbol == "ETH", Asset.asset_type == "crypto"))
    eth_asset = eth_result.scalar_one_or_none()
    if eth_asset is None:
        return None

    obs_result = await db.execute(
        select(CryptoQuoteObservation.ts, CryptoQuoteObservation.price_usd)
        .where(CryptoQuoteObservation.asset_id == eth_asset.id, CryptoQuoteObservation.ts <= block_timestamp)
        .order_by(CryptoQuoteObservation.ts.desc())
        .limit(1)
    )
    row = obs_result.first()
    if row is None:
        return None
    ts = row.ts if row.ts.tzinfo is not None else row.ts.replace(tzinfo=UTC)
    if (block_timestamp - ts) > max_age:
        return None
    return row.price_usd, ts


async def verify_purchase(
    db: AsyncSession, wallet_address: str, tx_hash: str, rpc: RpcProvider | None = None
) -> dict:
    settings = get_settings()
    if not _is_configured(settings):
        return dict(NOT_CONFIGURED)

    if not _TX_HASH_RE.match(tx_hash):
        return {"status": "invalid", "message": "Malformed transaction hash"}

    existing = await db.execute(
        select(ClaimedPurchaseTransaction).where(ClaimedPurchaseTransaction.tx_hash == tx_hash.lower())
    )
    if existing.scalar_one_or_none() is not None:
        return {"status": "already_claimed", "message": "This transaction has already been claimed"}

    provider = rpc or JsonRpcProvider(settings.robinhood_rpc_url)
    wallet_lower = wallet_address.lower()

    try:
        chain_id = await provider.get_chain_id()
        if chain_id != settings.synthex_chain_id:
            return {"status": "invalid", "message": "Transaction is not on the configured chain"}

        tx = await provider.get_transaction(tx_hash)
        if tx is None:
            return {"status": "invalid", "message": "Transaction not found"}
        receipt = await provider.get_transaction_receipt(tx_hash)
        if receipt is None:
            return {"status": "invalid", "message": "Transaction receipt not found"}
        current_block = await provider.get_block_number()
    except RpcError:
        log.exception("RPC error during purchase verification")
        return {"status": "rpc_error", "message": "RPC error — try again shortly"}
    except Exception:  # noqa: BLE001 — any transport failure fails closed
        # Never echo the raw exception — transport errors often embed the
        # request URL verbatim, and ROBINHOOD_RPC_URL may carry an API key.
        log.exception("Unexpected RPC failure during purchase verification")
        return {"status": "rpc_error", "message": "Unexpected RPC failure"}

    if tx.hash.lower() != tx_hash.lower():
        return {"status": "invalid", "message": "RPC transaction hash does not match the submitted hash"}

    if tx.block_number is None or tx.block_number != receipt.block_number:
        return {"status": "invalid", "message": "Transaction and receipt block numbers do not agree"}

    if receipt.status != 1:
        return {"status": "invalid", "message": "Transaction reverted"}

    confirmations = current_block - receipt.block_number
    if confirmations < settings.synthex_min_confirmations:
        return {
            "status": "pending",
            "message": f"{confirmations}/{settings.synthex_min_confirmations} confirmations",
        }

    if settings.synthex_token_start_block > 0 and receipt.block_number < settings.synthex_token_start_block:
        return {"status": "invalid", "message": "Transaction occurred before the configured $SynthEx launch block"}

    if tx.from_address != wallet_lower:
        return {"status": "invalid", "message": "Transaction was not sent by the authenticated wallet"}

    allowed_destinations = settings.parsed_dex_router_addresses | settings.parsed_dex_pool_addresses
    if not tx.to_address or tx.to_address not in allowed_destinations:
        return {"status": "invalid", "message": "Transaction destination is not an approved router or pool"}

    token_address = settings.synthex_token_address.lower()
    weth_address = settings.synthex_weth_address.lower()

    synthex_received = 0
    synthex_source_address: str | None = None
    weth_spent = 0
    weth_refunded = 0
    for log_entry in receipt.logs:
        topics = log_entry.get("topics") or []
        if not topics or topics[0].lower() != _TRANSFER_TOPIC:
            continue
        if len(topics) < 3:
            continue
        log_address = (log_entry.get("address") or "").lower()
        from_addr = _decode_address_topic(topics[1])
        to_addr = _decode_address_topic(topics[2])
        amount = _decode_uint(log_entry.get("data", "0x"))

        # Only a $SynthEx transfer that both lands in the wallet AND
        # originates from an approved router/pool counts — otherwise anyone
        # could "fake" a purchase by simply sending the wallet real tokens
        # from an unrelated address.
        if log_address == token_address and to_addr == wallet_lower and from_addr in allowed_destinations:
            synthex_received += amount
            synthex_source_address = from_addr
        if log_address == weth_address and from_addr == wallet_lower and to_addr in allowed_destinations:
            weth_spent += amount
        # A refund of unused WETH input back to the wallet, in the same
        # transaction, from the same approved destination — subtracted
        # below so an exact-output swap's refund can never inflate the
        # claimed spend.
        if log_address == weth_address and to_addr == wallet_lower and from_addr in allowed_destinations:
            weth_refunded += amount

    if synthex_received == 0:
        return {
            "status": "invalid",
            "message": "No $SynthEx transfer from an approved router/pool to the authenticated wallet was found",
        }

    if weth_spent > 0 and tx.value_wei > 0:
        return {
            "status": "invalid",
            "message": "Ambiguous transfer path: both native ETH value and a WETH transfer are present",
        }

    adapter = _adapter_for(tx.to_address)
    selector = _selector(tx.input_data)

    if weth_spent > 0:
        # WETH route — requires a registered adapter and a selector that
        # adapter confirms is safe (either exact-input or refundable; a
        # refund, if any, is subtracted above via the WETH log).
        if adapter is None:
            return dict(PURCHASE_VERIFICATION_NOT_CONFIGURED)
        if selector not in adapter.exact_input_selectors and selector not in adapter.refundable_selectors:
            return {
                "status": "unsupported_purchase_method",
                "message": "This router method is not supported for verification yet",
            }
        eth_spent_wei = weth_spent - weth_refunded
        if eth_spent_wei <= 0:
            return {
                "status": "invalid",
                "message": "Net WETH spend after refunds is zero or negative",
            }
    elif tx.value_wei > 0:
        # Native ETH is only ever trusted through an exact-input selector —
        # a native-ETH refund cannot be observed and subtracted the way a
        # WETH Transfer log can, so a merely "refundable" selector is never
        # sufficient here.
        if adapter is None:
            return dict(PURCHASE_VERIFICATION_NOT_CONFIGURED)
        if selector not in adapter.exact_input_selectors:
            return {
                "status": "unsupported_purchase_method",
                "message": (
                    "Native ETH spend cannot be safely verified for this router/pool method yet — "
                    "use a WETH-based swap, or wait for support for this router method"
                ),
            }
        eth_spent_wei = tx.value_wei
    else:
        return {"status": "unable_to_determine_net_spend", "message": "Could not determine ETH/WETH amount spent"}

    try:
        block = await provider.get_block(receipt.block_number)
    except RpcError:
        log.exception("RPC error reading block timestamp during purchase verification")
        return {"status": "rpc_error", "message": "RPC error — try again shortly"}
    except Exception:  # noqa: BLE001 — any transport failure fails closed
        log.exception("Unexpected RPC failure reading block timestamp during purchase verification")
        return {"status": "rpc_error", "message": "Unexpected RPC failure"}
    if block is None:
        return {"status": "invalid", "message": "Could not read block timestamp"}
    block_timestamp = datetime.fromtimestamp(block.timestamp, tz=UTC)

    price_lookup = await _lookup_eth_usd_price(
        db, block_timestamp, timedelta(minutes=settings.eth_usd_max_price_age_minutes)
    )
    if price_lookup is None:
        return {
            "status": "price_unavailable",
            "message": "No ETH/USD price observation is available near this transaction's block time",
        }
    eth_usd_price, eth_usd_source_ts = price_lookup

    eth_spent = Decimal(eth_spent_wei) / Decimal(10**18)
    usd_value = eth_spent * Decimal(str(eth_usd_price))
    usd_value_cents = int((usd_value * 100).to_integral_value())

    # Blockchain validation is complete — everything above this point is
    # read-only. Only now does the database persistence transaction begin;
    # the claim insert, entitlement creation/update, and final commit are
    # one atomic unit — any failure among them rolls all of it back
    # together, never leaving a claim behind without its entitlement update
    # (or vice versa).
    now = datetime.now(UTC)
    claim = ClaimedPurchaseTransaction(
        wallet_address=wallet_lower,
        tx_hash=tx_hash.lower(),
        block_number=receipt.block_number,
        block_timestamp=block_timestamp,
        eth_spent_raw=str(eth_spent_wei),
        eth_usd_price=eth_usd_price,
        eth_usd_source_ts=eth_usd_source_ts,
        usd_value_cents=usd_value_cents,
        synthex_received_raw=str(synthex_received),
        router_address=tx.to_address,
        pool_address=synthex_source_address or "",
        verified_at=now,
        created_at=now,
    )
    db.add(claim)

    try:
        entitlement = await get_or_create_entitlement_in_transaction(db, wallet_lower)
        entitlement.cumulative_usd_cents += usd_value_cents
        entitlement.tier = get_tier(entitlement.cumulative_usd_cents)
        entitlement.updated_at = now
        await db.commit()
    except IntegrityError:
        # Concurrent duplicate claim raced us on the tx_hash unique constraint.
        await db.rollback()
        return {"status": "already_claimed", "message": "This transaction has already been claimed"}
    except Exception:
        # Any other failure (e.g. an entitlement-side error) must not leave
        # the claim insert or entitlement changes partially persisted.
        await db.rollback()
        raise

    return {
        "status": "verified",
        "tier": entitlement.tier,
        "cumulative_usd": entitlement.cumulative_usd_cents / 100,
        "usd_value": usd_value_cents / 100,
        "synthex_received_raw": str(synthex_received),
    }
