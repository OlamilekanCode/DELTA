"""$SynthEx/ETH purchase verification. Fail-closed by design: until Robinhood
Chain's RPC URL, router/pool addresses and token contract are supplied via
environment variables, no purchase can ever be verified — this module must
never fabricate a successful verification or invent configuration values.

The verification pipeline itself (transaction/receipt/block fetch, log
decoding, router/pool/token checks, ETH/USD lookup, immutable claim storage)
is fully implemented and tested against a mocked RPC provider — only the
production RPC endpoint and contract addresses are missing.
"""

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
from app.services.portfolio import get_or_create_entitlement, get_tier

NOT_CONFIGURED = {
    "status": "not_configured",
    "message": "Purchase verification is not configured yet",
}

_TX_HASH_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")
_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


@dataclass(frozen=True)
class RouterAdapter:
    """Method selectors on a specific router/pool address that are confirmed
    (by reading the deployed contract source, not guessed) to consume the
    entire `msg.value` with no refund path — e.g. an "exact ETH in" swap. Any
    selector NOT listed here — including on an unregistered router — is
    treated as potentially refund-capable, so raw `tx.value` is never trusted
    as net spend without this explicit proof."""

    exact_input_selectors: frozenset[str]


# Populate only once a real Robinhood Chain router/pool address and its
# audited method selectors are confirmed — never guessed or assumed from a
# generic ABI. Empty means every native-ETH purchase currently returns
# unsupported_purchase_method; WETH-Transfer-log-based purchases are exact by
# construction and don't depend on this registry at all.
ROUTER_ADAPTERS: dict[str, RouterAdapter] = {}


def _native_eth_fully_consumed(destination_address: str | None, input_data: str) -> bool:
    if not destination_address:
        return False
    adapter = ROUTER_ADAPTERS.get(destination_address.lower())
    if adapter is None:
        return False
    selector = (input_data or "0x")[:10].lower()
    return selector in adapter.exact_input_selectors


def _decode_address_topic(topic: str) -> str:
    return "0x" + topic[-40:].lower()


def _decode_uint(data: str) -> int:
    return int(data, 16) if data and data != "0x" else 0


def _is_configured(settings) -> bool:
    # A missing/zero launch block in production would let a pre-launch or
    # unrelated historical transaction be claimed as a $SynthEx purchase —
    # fail closed rather than allow verification without it.
    if settings.app_env == "production" and settings.synthex_token_start_block <= 0:
        return False
    return bool(
        settings.synthex_chain_id
        and settings.robinhood_rpc_url
        and settings.synthex_token_address
        and settings.parsed_dex_router_addresses | settings.parsed_dex_pool_addresses
        and settings.synthex_weth_address
    )


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
    except RpcError as e:
        return {"status": "rpc_error", "message": str(e)}
    except Exception as e:  # noqa: BLE001 — any transport failure fails closed
        return {"status": "rpc_error", "message": f"unexpected RPC failure: {e}"}

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
    for log in receipt.logs:
        topics = log.get("topics") or []
        if not topics or topics[0].lower() != _TRANSFER_TOPIC:
            continue
        if len(topics) < 3:
            continue
        log_address = (log.get("address") or "").lower()
        from_addr = _decode_address_topic(topics[1])
        to_addr = _decode_address_topic(topics[2])
        amount = _decode_uint(log.get("data", "0x"))

        # Only a $SynthEx transfer that both lands in the wallet AND
        # originates from an approved router/pool counts — otherwise anyone
        # could "fake" a purchase by simply sending the wallet real tokens
        # from an unrelated address.
        if log_address == token_address and to_addr == wallet_lower and from_addr in allowed_destinations:
            synthex_received += amount
            synthex_source_address = from_addr
        if log_address == weth_address and from_addr == wallet_lower and to_addr in allowed_destinations:
            weth_spent += amount

    if synthex_received == 0:
        return {
            "status": "invalid",
            "message": "No $SynthEx transfer from an approved router/pool to the authenticated wallet was found",
        }

    # ETH spent: a WETH Transfer log is exact by construction (no refund
    # ambiguity). Native ETH's tx.value is only trusted when the destination
    # router/pool and called method are confirmed (via ROUTER_ADAPTERS) to
    # consume the full value with no refund — otherwise we cannot safely
    # rule out an excess-ETH refund inflating the claimed spend, so we
    # decline rather than guess.
    if weth_spent > 0:
        eth_spent_wei = weth_spent
    elif tx.value_wei > 0:
        if not _native_eth_fully_consumed(tx.to_address, tx.input_data):
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

    block = await provider.get_block(receipt.block_number)
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

    entitlement = await get_or_create_entitlement(db, wallet_lower)
    entitlement.cumulative_usd_cents += usd_value_cents
    entitlement.tier = get_tier(entitlement.cumulative_usd_cents)
    entitlement.updated_at = now

    try:
        await db.commit()
    except IntegrityError:
        # Concurrent duplicate claim raced us on the tx_hash unique constraint.
        await db.rollback()
        return {"status": "already_claimed", "message": "This transaction has already been claimed"}

    return {
        "status": "verified",
        "tier": entitlement.tier,
        "cumulative_usd": entitlement.cumulative_usd_cents / 100,
        "usd_value": usd_value_cents / 100,
        "synthex_received_raw": str(synthex_received),
    }
