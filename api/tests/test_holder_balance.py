"""Tests for the real (but fail-closed) holder-balance verification pipeline."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.auth import CachedWalletBalance
from app.services import holder as holder_service
from app.services.blockchain import MockRpcProvider, RpcError
from app.services.holder import is_verified_holder, refresh_wallet_balance

WALLET = "0x" + "1" * 40
TOKEN = "0x" + "9" * 40
CHAIN_ID = 8453
MIN_BALANCE_RAW = "1000000000000000000000"  # 1000 tokens @ 18 decimals


def _configured_settings(**overrides) -> Settings:
    fields = dict(
        synthex_chain_id=CHAIN_ID,
        synthex_token_address=TOKEN,
        synthex_holder_min_balance_raw=MIN_BALANCE_RAW,
        robinhood_rpc_url="https://rpc.example.invalid",
        database_url="sqlite+aiosqlite:///./test.db",
    )
    fields.update(overrides)
    return Settings(**fields)


@pytest.fixture()
def configured(monkeypatch):
    settings = _configured_settings()
    monkeypatch.setattr(holder_service, "get_settings", lambda: settings)
    return settings


@pytest.mark.asyncio
async def test_refresh_not_configured_by_default(db: AsyncSession) -> None:
    """Default test settings have no chain/token/RPC configured."""
    result = await refresh_wallet_balance(db, WALLET)
    assert result.status == "not_configured"


@pytest.mark.asyncio
async def test_refresh_sufficient_balance_marks_holder(db: AsyncSession, configured) -> None:
    mock = MockRpcProvider(
        chain_id=CHAIN_ID,
        block_number=12345,
        balances={(TOKEN.lower(), WALLET.lower()): int(MIN_BALANCE_RAW) + 1},
    )
    result = await refresh_wallet_balance(db, WALLET, rpc=mock)
    assert result.status == "ok"
    assert result.is_holder is True
    assert result.block_number == 12345

    row = (await db.execute(select(CachedWalletBalance).where(CachedWalletBalance.wallet_address == WALLET.lower()))).scalar_one()
    assert row.is_holder is True
    assert row.checked_block_number == 12345
    assert await is_verified_holder(db, WALLET) is True


@pytest.mark.asyncio
async def test_refresh_zero_balance_not_holder(db: AsyncSession, configured) -> None:
    mock = MockRpcProvider(chain_id=CHAIN_ID, balances={})
    result = await refresh_wallet_balance(db, WALLET, rpc=mock)
    assert result.status == "ok"
    assert result.is_holder is False
    assert result.balance_raw == "0"


@pytest.mark.asyncio
async def test_refresh_insufficient_balance_not_holder(db: AsyncSession, configured) -> None:
    mock = MockRpcProvider(
        chain_id=CHAIN_ID,
        balances={(TOKEN.lower(), WALLET.lower()): int(MIN_BALANCE_RAW) - 1},
    )
    result = await refresh_wallet_balance(db, WALLET, rpc=mock)
    assert result.is_holder is False


@pytest.mark.asyncio
async def test_refresh_wrong_chain_returns_chain_mismatch(db: AsyncSession, configured) -> None:
    mock = MockRpcProvider(chain_id=999999, balances={(TOKEN.lower(), WALLET.lower()): int(MIN_BALANCE_RAW) * 10})
    result = await refresh_wallet_balance(db, WALLET, rpc=mock)
    assert result.status == "chain_mismatch"


@pytest.mark.asyncio
async def test_refresh_rpc_error_fails_closed(db: AsyncSession, configured) -> None:
    mock = MockRpcProvider(chain_id=CHAIN_ID, raise_on_call=RpcError("boom"))
    result = await refresh_wallet_balance(db, WALLET, rpc=mock)
    assert result.status == "rpc_error"


@pytest.mark.asyncio
async def test_refresh_rpc_timeout_fails_closed_not_crash(db: AsyncSession, configured) -> None:
    mock = MockRpcProvider(chain_id=CHAIN_ID, raise_on_call=TimeoutError("timed out"))
    result = await refresh_wallet_balance(db, WALLET, rpc=mock)
    assert result.status == "rpc_error"


@pytest.mark.asyncio
async def test_refresh_malformed_response_fails_closed(db: AsyncSession, configured) -> None:
    mock = MockRpcProvider(chain_id=CHAIN_ID, raise_on_call=ValueError("bad hex"))
    result = await refresh_wallet_balance(db, WALLET, rpc=mock)
    assert result.status == "rpc_error"


@pytest.mark.asyncio
async def test_stale_cache_is_not_holder(db: AsyncSession, configured) -> None:
    db.add(CachedWalletBalance(
        wallet_address=WALLET.lower(),
        token_address=TOKEN.lower(),
        balance_raw=str(int(MIN_BALANCE_RAW) * 10),
        checked_at=datetime.now(UTC) - timedelta(minutes=30),
        checked_block_number=1,
        is_holder=True,
    ))
    await db.commit()
    assert await is_verified_holder(db, WALLET) is False


@pytest.mark.asyncio
async def test_successful_refresh_then_holder_check(db: AsyncSession, configured) -> None:
    assert await is_verified_holder(db, WALLET) is False
    mock = MockRpcProvider(chain_id=CHAIN_ID, balances={(TOKEN.lower(), WALLET.lower()): int(MIN_BALANCE_RAW) * 2})
    await refresh_wallet_balance(db, WALLET, rpc=mock)
    assert await is_verified_holder(db, WALLET) is True


@pytest.mark.asyncio
async def test_refresh_upserts_not_duplicates(db: AsyncSession, configured) -> None:
    mock = MockRpcProvider(chain_id=CHAIN_ID, balances={(TOKEN.lower(), WALLET.lower()): 5})
    await refresh_wallet_balance(db, WALLET, rpc=mock)
    mock2 = MockRpcProvider(chain_id=CHAIN_ID, balances={(TOKEN.lower(), WALLET.lower()): 10})
    await refresh_wallet_balance(db, WALLET, rpc=mock2)

    rows = (await db.execute(select(CachedWalletBalance).where(CachedWalletBalance.wallet_address == WALLET.lower()))).scalars().all()
    assert len(rows) == 1
    assert rows[0].balance_raw == "10"


@pytest.mark.asyncio
async def test_balance_never_uses_float(db: AsyncSession, configured) -> None:
    """A balance large enough to lose precision as a float must still compare exactly."""
    huge = 2**90  # far beyond float64 exact-integer precision
    mock = MockRpcProvider(chain_id=CHAIN_ID, balances={(TOKEN.lower(), WALLET.lower()): huge})
    result = await refresh_wallet_balance(db, WALLET, rpc=mock)
    assert result.balance_raw == str(huge)
    assert result.is_holder is True
