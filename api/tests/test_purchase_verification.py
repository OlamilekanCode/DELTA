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
from app.services.purchase_verification import verify_purchase

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
    from_address=WALLET,
    to_address=ROUTER,
    value_wei=0,
    status=1,
    logs=None,
    block_timestamp=None,
) -> MockRpcProvider:
    ts = block_timestamp or datetime.now(UTC)
    return MockRpcProvider(
        chain_id=chain_id,
        block_number=block_number,
        transactions={TX_HASH.lower(): TransactionData(
            hash=TX_HASH, from_address=from_address.lower(), to_address=to_address.lower() if to_address else None,
            value_wei=value_wei, block_number=tx_block, input_data="0x",
        )},
        receipts={TX_HASH.lower(): TransactionReceipt(status=status, block_number=tx_block, logs=logs or [])},
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


@pytest.mark.asyncio
async def test_verify_purchase_success(db: AsyncSession, configured) -> None:
    now = datetime.now(UTC)
    await _seed_eth_price(db, now - timedelta(seconds=5))
    mock = _mock_provider(
        value_wei=10**18,  # 1 ETH direct
        logs=[_transfer_log(TOKEN, ROUTER, WALLET, 500 * 10**18)],
        block_timestamp=now,
    )
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "verified"
    assert result["usd_value"] == pytest.approx(3000.0, rel=1e-6)
    assert result["synthex_received_raw"] == str(500 * 10**18)

    row = (await db.execute(select(ClaimedPurchaseTransaction).where(ClaimedPurchaseTransaction.tx_hash == TX_HASH.lower()))).scalar_one()
    assert row.wallet_address == WALLET.lower()
    assert row.usd_value_cents == 300000


@pytest.mark.asyncio
async def test_verify_purchase_via_weth_swap(db: AsyncSession, configured) -> None:
    now = datetime.now(UTC)
    await _seed_eth_price(db, now - timedelta(seconds=5))
    mock = _mock_provider(
        value_wei=0,
        logs=[
            _transfer_log(WETH, WALLET, ROUTER, 2 * 10**18),
            _transfer_log(TOKEN, ROUTER, WALLET, 1000 * 10**18),
        ],
        block_timestamp=now,
    )
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "verified"
    assert result["usd_value"] == pytest.approx(6000.0, rel=1e-6)


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
async def test_verify_purchase_price_unavailable(db: AsyncSession, configured) -> None:
    old_ts = datetime.now(UTC) - timedelta(days=400)
    mock = _mock_provider(value_wei=10**18, logs=[_transfer_log(TOKEN, ROUTER, WALLET, 1)], block_timestamp=old_ts)
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
async def test_verify_purchase_updates_entitlement_tier(db: AsyncSession, configured) -> None:
    now = datetime.now(UTC)
    await _seed_eth_price(db, now - timedelta(seconds=5), price=100.0)
    # 1 ETH * $100 = $100 → within the $50-$249.99 "summary" tier
    mock = _mock_provider(value_wei=10**18, logs=[_transfer_log(TOKEN, ROUTER, WALLET, 1000 * 10**18)], block_timestamp=now)
    result = await verify_purchase(db, WALLET, TX_HASH, rpc=mock)
    assert result["status"] == "verified"
    assert result["tier"] == "summary"
