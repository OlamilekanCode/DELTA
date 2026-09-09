from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.asset import Asset
from app.models.crypto_observation import CryptoQuoteObservation
from app.models.purchase import ClaimedPurchaseTransaction
from app.services import purchase_verification as pv_module
from app.services.blockchain import BlockData, MockRpcProvider, TransactionData, TransactionReceipt
from app.services.purchase_verification import RouterAdapter, verify_purchase

WALLET = "0x" + "1" * 40
TOKEN = "0x" + "2" * 40
ROUTER = "0x" + "3" * 40
WETH = "0x" + "4" * 40
CHAIN_ID = 8453
TX_HASH = "0x" + "a" * 64

_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def _configured_settings(**overrides) -> Settings:
    fields = dict(
        synthex_chain_id=CHAIN_ID,
        robinhood_rpc_url="https://rpc.example.invalid",
        synthex_token_address=TOKEN,
        synthex_dex_router_addresses=ROUTER,
        synthex_weth_address=WETH,
        synthex_min_confirmations=1,
        database_url="sqlite+aiosqlite:///./test.db",
    )
    fields.update(overrides)
    return Settings(**fields)


def _pad(addr: str) -> str:
    return "0x" + addr.lower().replace("0x", "").rjust(64, "0")


def _transfer_log(token_address: str, from_addr: str, to_addr: str, amount: int) -> dict:
    return {
        "address": token_address,
        "topics": [_TRANSFER_TOPIC, _pad(from_addr), _pad(to_addr)],
        "data": hex(amount),
    }


@pytest.fixture()
def configured(monkeypatch):
    settings = _configured_settings()
    monkeypatch.setattr(pv_module, "get_settings", lambda: settings)
    return settings


async def _seed_eth_price(db: AsyncSession, ts: datetime, price: float = 3000.0) -> None:
    eth = (await db.execute(select(Asset).where(Asset.symbol == "ETH"))).scalar_one()
    db.add(CryptoQuoteObservation(asset_id=eth.id, ts=ts, price_usd=price, is_demo=False))
    await db.commit()


def _mock_provider(
    *,
    chain_id=CHAIN_ID,
    block_number=1000,
    tx_block=990,
    receipt_block=None,
    from_address=WALLET,
    to_address=ROUTER,
    value_wei=0,
    status=1,
    logs=None,
    block_timestamp=None,
    input_data="0x",
    tx_hash_field=None,
) -> MockRpcProvider:
    ts = block_timestamp or datetime.now(UTC)
    return MockRpcProvider(
        chain_id=chain_id,
        block_number=block_number,
        transactions={TX_HASH.lower(): TransactionData(
            hash=tx_hash_field or TX_HASH, from_address=from_address.lower(),
            to_address=to_address.lower() if to_address else None,
            value_wei=value_wei, block_number=tx_block, input_data=input_data,
        )},
        receipts={TX_HASH.lower(): TransactionReceipt(
            status=status, block_number=receipt_block if receipt_block is not None else tx_block, logs=logs or [],
        )},
        blocks={tx_block: BlockData(number=tx_block, timestamp=int(ts.timestamp()))},
    )


@pytest.mark.asyncio
async def test_verify_purchase_fails_closed_when_unconfigured(db: AsyncSession) -> None:
    result = await verify_purchase(db, "0x" + "1" * 40, "0x" + "a" * 64)
    assert result["status"] == "not_configured"
    assert result["message"] == "Purchase verification is not configured yet"


@pytest.mark.asyncio
async def test_verify_purchase_never_returns_verified_without_config(db: AsyncSession) -> None:
    result = await verify_purchase(db, "0x" + "2" * 40, "0x" + "b" * 64)
    assert result["status"] != "verified"


@pytest.mark.asyncio
async def test_verify_purchase_rejects_malformed_hash(db: AsyncSession, configured) -> None:
    result = await verify_purchase(db, WALLET, "not-a-hash")
    assert result["status"] == "invalid"


_EXACT_ETH_IN_SELECTOR = "0x7ff36ab5"  # e.g. swapExactETHForTokens — full msg.value consumed, no refund


@pytest.mark.asyncio
async def test_verify_purchase_success_native_eth_via_confirmed_adapter(db: AsyncSession, configured, monkeypatch) -> None:
    """Native ETH is only trusted once the destination router/pool and the
    exact method called are confirmed (via ROUTER_ADAPTERS) to consume the
    entire msg.value with no refund path."""
    monkeypatch.setitem(
        pv_module.ROUTER_ADAPTERS, ROUTER.lower(), RouterAdapter(exact_input_selectors=frozenset({_EXACT_ETH_IN_SELECTOR}))
    )
    now = datetime.now(UTC)
    await _seed_eth_price(db, now - timedelta(seconds=5))
    mock = _mock_provider(
        value_wei=10**18,  # 1 ETH direct
        logs=[_transfer_log(TOKEN, ROUTER, WALLET, 500 * 10**18)],
        block_timestamp=now,
        input_data=_EXACT_ETH_IN_SELECTOR + "0" * 56,
    )
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "verified"
    assert result["usd_value"] == pytest.approx(3000.0, rel=1e-6)
    assert result["synthex_received_raw"] == str(500 * 10**18)

    row = (await db.execute(select(ClaimedPurchaseTransaction).where(ClaimedPurchaseTransaction.tx_hash == TX_HASH.lower()))).scalar_one()
    assert row.wallet_address == WALLET.lower()
    assert row.usd_value_cents == 300000
    assert row.pool_address == ROUTER.lower()  # real transfer-log source, not just copied from tx.to


@pytest.mark.asyncio
async def test_verify_purchase_rejects_native_eth_with_no_registered_adapter(db: AsyncSession, configured) -> None:
    """No router/pool has a confirmed adapter yet (ROUTER_ADAPTERS starts
    empty) — native ETH must never be trusted by default, and must fail
    closed as "not configured" rather than a method-specific rejection."""
    mock = _mock_provider(value_wei=10**18, logs=[_transfer_log(TOKEN, ROUTER, WALLET, 500 * 10**18)])
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "purchase_verification_not_configured"


@pytest.mark.asyncio
async def test_verify_purchase_rejects_refund_capable_native_eth_method(db: AsyncSession, configured, monkeypatch) -> None:
    """Even with an adapter registered for this router, a method selector
    NOT in its exact-input set (e.g. one that can refund excess ETH) must
    never be trusted — raw tx.value could overstate the real spend."""
    monkeypatch.setitem(
        pv_module.ROUTER_ADAPTERS, ROUTER.lower(), RouterAdapter(exact_input_selectors=frozenset({_EXACT_ETH_IN_SELECTOR}))
    )
    refund_capable_selector = "0xfb3bdb41"  # e.g. swapETHForExactTokens — can refund unused ETH
    mock = _mock_provider(
        value_wei=10**18,
        logs=[_transfer_log(TOKEN, ROUTER, WALLET, 500 * 10**18)],
        input_data=refund_capable_selector + "0" * 56,
    )
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "unsupported_purchase_method"


_WETH_EXACT_IN_SELECTOR = "0x38ed1739"  # e.g. swapExactTokensForTokens — full WETH-in consumed, no refund
_WETH_REFUNDABLE_SELECTOR = "0x8803dbee"  # e.g. swapTokensForExactTokens — may refund unused WETH input


def _with_weth_adapter(monkeypatch, **kwargs) -> None:
    monkeypatch.setitem(pv_module.ROUTER_ADAPTERS, ROUTER.lower(), RouterAdapter(**kwargs))


@pytest.mark.asyncio
async def test_verify_purchase_via_weth_swap_exact_input(db: AsyncSession, configured, monkeypatch) -> None:
    """A supported exact-input WETH route with no refund log is trusted for
    its full transferred amount."""
    _with_weth_adapter(monkeypatch, exact_input_selectors=frozenset({_WETH_EXACT_IN_SELECTOR}))
    now = datetime.now(UTC)
    await _seed_eth_price(db, now - timedelta(seconds=5))
    mock = _mock_provider(
        value_wei=0,
        logs=[
            _transfer_log(WETH, WALLET, ROUTER, 2 * 10**18),
            _transfer_log(TOKEN, ROUTER, WALLET, 1000 * 10**18),
        ],
        block_timestamp=now,
        input_data=_WETH_EXACT_IN_SELECTOR + "0" * 56,
    )
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "verified"
    assert result["usd_value"] == pytest.approx(6000.0, rel=1e-6)


@pytest.mark.asyncio
async def test_verify_purchase_weth_exact_output_subtracts_refund(db: AsyncSession, configured, monkeypatch) -> None:
    """An exact-output WETH swap can refund unused input in the same
    transaction — the verified spend must be net of that refund, never the
    gross amount transferred out."""
    _with_weth_adapter(monkeypatch, refundable_selectors=frozenset({_WETH_REFUNDABLE_SELECTOR}))
    now = datetime.now(UTC)
    await _seed_eth_price(db, now - timedelta(seconds=5), price=1000.0)
    mock = _mock_provider(
        value_wei=0,
        logs=[
            _transfer_log(WETH, WALLET, ROUTER, 5 * 10**18),   # gross sent
            _transfer_log(WETH, ROUTER, WALLET, 2 * 10**18),   # refund of unused input
            _transfer_log(TOKEN, ROUTER, WALLET, 1000 * 10**18),
        ],
        block_timestamp=now,
        input_data=_WETH_REFUNDABLE_SELECTOR + "0" * 56,
    )
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "verified"
    # net = 5 - 2 = 3 ETH * $1000 = $3000, not 5 * $1000 = $5000
    assert result["usd_value"] == pytest.approx(3000.0, rel=1e-6)


@pytest.mark.asyncio
async def test_verify_purchase_weth_refund_inflated_to_zero_rejected(db: AsyncSession, configured, monkeypatch) -> None:
    """A refund equal to (or exceeding) the gross amount sent must never be
    accepted as a positive purchase."""
    _with_weth_adapter(monkeypatch, refundable_selectors=frozenset({_WETH_REFUNDABLE_SELECTOR}))
    mock = _mock_provider(
        value_wei=0,
        logs=[
            _transfer_log(WETH, WALLET, ROUTER, 2 * 10**18),
            _transfer_log(WETH, ROUTER, WALLET, 2 * 10**18),  # full refund — net spend is zero
            _transfer_log(TOKEN, ROUTER, WALLET, 1000 * 10**18),
        ],
        input_data=_WETH_REFUNDABLE_SELECTOR + "0" * 56,
    )
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "invalid"


@pytest.mark.asyncio
async def test_verify_purchase_weth_unrelated_transfer_not_counted(db: AsyncSession, configured, monkeypatch) -> None:
    """A WETH transfer from the wallet to some unrelated (non-approved)
    address in the same transaction must never count as purchase spend."""
    _with_weth_adapter(monkeypatch, exact_input_selectors=frozenset({_WETH_EXACT_IN_SELECTOR}))
    unrelated = "0x" + "d" * 40
    mock = _mock_provider(
        value_wei=0,
        logs=[
            _transfer_log(WETH, WALLET, unrelated, 2 * 10**18),
            _transfer_log(TOKEN, ROUTER, WALLET, 1000 * 10**18),
        ],
        input_data=_WETH_EXACT_IN_SELECTOR + "0" * 56,
    )
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "unable_to_determine_net_spend"


@pytest.mark.asyncio
async def test_verify_purchase_weth_unsupported_router_method(db: AsyncSession, configured, monkeypatch) -> None:
    """An adapter is registered for this router, but not for the specific
    method actually called — must fail as unsupported, not silently
    verified."""
    _with_weth_adapter(monkeypatch, exact_input_selectors=frozenset({_WETH_EXACT_IN_SELECTOR}))
    other_selector = "0xdeadbeef"
    mock = _mock_provider(
        value_wei=0,
        logs=[
            _transfer_log(WETH, WALLET, ROUTER, 2 * 10**18),
            _transfer_log(TOKEN, ROUTER, WALLET, 1000 * 10**18),
        ],
        input_data=other_selector + "0" * 56,
    )
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "unsupported_purchase_method"


@pytest.mark.asyncio
async def test_verify_purchase_ambiguous_both_native_and_weth_rejected(db: AsyncSession, configured, monkeypatch) -> None:
    _with_weth_adapter(monkeypatch, exact_input_selectors=frozenset({_WETH_EXACT_IN_SELECTOR}))
    mock = _mock_provider(
        value_wei=10**18,
        logs=[
            _transfer_log(WETH, WALLET, ROUTER, 2 * 10**18),
            _transfer_log(TOKEN, ROUTER, WALLET, 1000 * 10**18),
        ],
        input_data=_WETH_EXACT_IN_SELECTOR + "0" * 56,
    )
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "invalid"


@pytest.mark.asyncio
async def test_verify_purchase_rejects_reverted_tx(db: AsyncSession, configured) -> None:
    mock = _mock_provider(status=0, logs=[_transfer_log(TOKEN, ROUTER, WALLET, 1)])
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "invalid"


@pytest.mark.asyncio
async def test_verify_purchase_rejects_wrong_chain(db: AsyncSession, configured) -> None:
    mock = _mock_provider(chain_id=1, logs=[_transfer_log(TOKEN, ROUTER, WALLET, 1)])
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "invalid"


@pytest.mark.asyncio
async def test_verify_purchase_pending_confirmations(db: AsyncSession, monkeypatch) -> None:
    settings = _configured_settings(synthex_min_confirmations=50)
    monkeypatch.setattr(pv_module, "get_settings", lambda: settings)
    mock = _mock_provider(block_number=1000, tx_block=990, logs=[_transfer_log(TOKEN, ROUTER, WALLET, 1)])
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "pending"


@pytest.mark.asyncio
async def test_verify_purchase_rejects_wrong_sender(db: AsyncSession, configured) -> None:
    other_wallet = "0x" + "9" * 40
    mock = _mock_provider(from_address=other_wallet, logs=[_transfer_log(TOKEN, ROUTER, WALLET, 1)])
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "invalid"


@pytest.mark.asyncio
async def test_verify_purchase_rejects_wrong_destination(db: AsyncSession, configured) -> None:
    random_contract = "0x" + "7" * 40
    mock = _mock_provider(to_address=random_contract, logs=[_transfer_log(TOKEN, random_contract, WALLET, 1)])
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "invalid"


@pytest.mark.asyncio
async def test_verify_purchase_rejects_missing_synthex_transfer(db: AsyncSession, configured) -> None:
    mock = _mock_provider(value_wei=10**18, logs=[])
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "invalid"


@pytest.mark.asyncio
async def test_verify_purchase_rejects_unrelated_token_transfer(db: AsyncSession, configured) -> None:
    """A transfer of some other ERC-20 to the wallet must never count as a $SynthEx purchase."""
    fake_token = "0x" + "5" * 40
    mock = _mock_provider(value_wei=10**18, logs=[_transfer_log(fake_token, ROUTER, WALLET, 999 * 10**18)])
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "invalid"


@pytest.mark.asyncio
async def test_verify_purchase_rejects_spoofed_synthex_transfer(db: AsyncSession, configured) -> None:
    """A real $SynthEx transfer sent to the wallet from an address that is
    NOT an approved router/pool must never count — otherwise anyone could
    fake a "purchase" by just sending the wallet tokens directly."""
    unapproved_source = "0x" + "6" * 40
    mock = _mock_provider(logs=[_transfer_log(TOKEN, unapproved_source, WALLET, 500 * 10**18)])
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "invalid"


@pytest.mark.asyncio
async def test_verify_purchase_rejects_wrong_pool_source(db: AsyncSession, monkeypatch) -> None:
    """The transaction destination (tx.to) can be an approved router while
    the $SynthEx transfer's actual on-chain source is a different,
    unapproved pool — the destination check alone is not enough."""
    other_pool = "0x" + "8" * 40
    settings = _configured_settings(synthex_dex_pool_addresses=other_pool)
    monkeypatch.setattr(pv_module, "get_settings", lambda: settings)
    # ROUTER is approved as a router destination, but the token transfer log
    # claims to originate from an address that is neither ROUTER nor the
    # approved pool.
    unapproved_source = "0x" + "6" * 40
    mock = _mock_provider(to_address=ROUTER, logs=[_transfer_log(TOKEN, unapproved_source, WALLET, 1)])
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "invalid"


@pytest.mark.asyncio
async def test_verify_purchase_rejects_tx_receipt_block_mismatch(db: AsyncSession, configured) -> None:
    mock = _mock_provider(tx_block=990, receipt_block=991, logs=[_transfer_log(TOKEN, ROUTER, WALLET, 1)])
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "invalid"


@pytest.mark.asyncio
async def test_verify_purchase_rejects_tx_hash_mismatch(db: AsyncSession, configured) -> None:
    """Defends against a misbehaving/compromised RPC returning a transaction
    object for a different hash than the one requested."""
    other_hash = "0x" + "f" * 64
    mock = _mock_provider(tx_hash_field=other_hash, logs=[_transfer_log(TOKEN, ROUTER, WALLET, 1)])
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "invalid"


@pytest.mark.asyncio
async def test_verify_purchase_rejects_pre_launch_block(db: AsyncSession, monkeypatch) -> None:
    settings = _configured_settings(synthex_token_start_block=1000)
    monkeypatch.setattr(pv_module, "get_settings", lambda: settings)
    mock = _mock_provider(tx_block=990, logs=[_transfer_log(TOKEN, ROUTER, WALLET, 1)])
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "invalid"


@pytest.mark.asyncio
async def test_verify_purchase_unable_to_determine_net_spend(db: AsyncSession, configured) -> None:
    """A genuine $SynthEx transfer exists, but there is no native ETH value
    and no WETH Transfer log to account for what was spent — must decline
    rather than guess a spend amount."""
    mock = _mock_provider(value_wei=0, logs=[_transfer_log(TOKEN, ROUTER, WALLET, 500 * 10**18)])
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "unable_to_determine_net_spend"


@pytest.mark.asyncio
async def test_verify_purchase_production_requires_start_block(db: AsyncSession, monkeypatch) -> None:
    settings = _configured_settings(app_env="production", synthex_token_start_block=0)
    monkeypatch.setattr(pv_module, "get_settings", lambda: settings)
    result = await verify_purchase(db, WALLET, TX_HASH)
    assert result["status"] == "not_configured"


@pytest.mark.asyncio
async def test_verify_purchase_price_unavailable(db: AsyncSession, configured, monkeypatch) -> None:
    _with_weth_adapter(monkeypatch, exact_input_selectors=frozenset({_WETH_EXACT_IN_SELECTOR}))
    old_ts = datetime.now(UTC) - timedelta(days=400)
    mock = _mock_provider(
        value_wei=0,
        logs=[_transfer_log(WETH, WALLET, ROUTER, 1), _transfer_log(TOKEN, ROUTER, WALLET, 1)],
        block_timestamp=old_ts,
        input_data=_WETH_EXACT_IN_SELECTOR + "0" * 56,
    )
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "price_unavailable"


@pytest.mark.asyncio
async def test_verify_purchase_already_claimed(db: AsyncSession, configured) -> None:
    now = datetime.now(UTC)
    db.add(ClaimedPurchaseTransaction(
        wallet_address=WALLET.lower(), tx_hash=TX_HASH.lower(), block_number=1, block_timestamp=now,
        eth_spent_raw="1", eth_usd_price=3000.0, eth_usd_source_ts=now, usd_value_cents=100,
        synthex_received_raw="1", router_address=ROUTER, pool_address="", verified_at=now, created_at=now,
    ))
    await db.commit()

    mock = _mock_provider(logs=[_transfer_log(TOKEN, ROUTER, WALLET, 1)])
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "already_claimed"


@pytest.mark.asyncio
async def test_verify_purchase_updates_entitlement_tier(db: AsyncSession, configured, monkeypatch) -> None:
    _with_weth_adapter(monkeypatch, exact_input_selectors=frozenset({_WETH_EXACT_IN_SELECTOR}))
    now = datetime.now(UTC)
    await _seed_eth_price(db, now - timedelta(seconds=5), price=100.0)
    # 1 ETH * $100 = $100 → within the $50-$249.99 "summary" tier
    mock = _mock_provider(
        value_wei=0,
        logs=[
            _transfer_log(WETH, WALLET, ROUTER, 10**18),
            _transfer_log(TOKEN, ROUTER, WALLET, 1000 * 10**18),
        ],
        block_timestamp=now,
        input_data=_WETH_EXACT_IN_SELECTOR + "0" * 56,
    )
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "verified"
    assert result["tier"] == "summary"


@pytest.mark.asyncio
async def test_verify_purchase_entitlement_failure_leaves_no_orphaned_claim(db: AsyncSession, configured, monkeypatch) -> None:
    """If anything fails after the claim is staged but before the single
    final commit, no claim row must be left behind without its matching
    entitlement update."""
    _with_weth_adapter(monkeypatch, exact_input_selectors=frozenset({_WETH_EXACT_IN_SELECTOR}))
    now = datetime.now(UTC)
    await _seed_eth_price(db, now - timedelta(seconds=5))
    mock = _mock_provider(
        value_wei=0,
        logs=[
            _transfer_log(WETH, WALLET, ROUTER, 10**18),
            _transfer_log(TOKEN, ROUTER, WALLET, 1000 * 10**18),
        ],
        block_timestamp=now,
        input_data=_WETH_EXACT_IN_SELECTOR + "0" * 56,
    )

    def boom(*_args, **_kwargs):
        raise RuntimeError("simulated entitlement-side failure")

    monkeypatch.setattr(pv_module, "get_tier", boom)

    with pytest.raises(RuntimeError):
        await verify_purchase(db, WALLET, TX_HASH, rpc=mock)

    row = (await db.execute(
        select(ClaimedPurchaseTransaction).where(ClaimedPurchaseTransaction.tx_hash == TX_HASH.lower())
    )).scalar_one_or_none()
    assert row is None
