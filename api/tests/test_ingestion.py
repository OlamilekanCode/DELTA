"""
Ingestion tests covering:
- Provider selection logic (_get_provider)
- DB persistence after ingest_asset (rows inserted, is_demo correct)
- Real-mode end-to-end: mocked HTTP → ingest → API returns demo=False
"""
import re
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.config import Settings
from app.ingestion.runner import (
    _get_provider,
    ingest_asset,
    seed_asset_catalogue,
    seed_fixture_data,
)
from app.models.asset import Asset
from app.models.price import DailyPrice
from app.providers.coingecko import CoinGeckoProvider
from app.providers.fixtures import FixtureProvider
from app.providers.marketstack import MarketstackProvider
from app.services.correlation import MIN_OBSERVATIONS

# ── Helpers ─────────────────────────────────────────────────────────────────

def _ts_ms(d: date) -> int:
    """UTC midnight timestamp in milliseconds for a given date."""
    dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


_FIXTURE_START = date(2026, 6, 3)  # matches fixtures.py _START_DATE


def _coingecko_response(n: int = 63) -> dict:
    """Consecutive daily dates from fixture _START_DATE so upsert covers all fixture rows."""
    return {
        "prices": [
            [_ts_ms(_FIXTURE_START + timedelta(days=i)), 50000.0 + i * 100]
            for i in range(n)
        ]
    }


def _marketstack_response(n: int = 63) -> dict:
    """Consecutive daily dates from fixture _START_DATE (matching fixture pattern, not weekdays-only)."""
    return {
        "data": [
            {
                "date": (_FIXTURE_START + timedelta(days=i)).isoformat() + "T00:00:00+0000",
                "close": 500.0 + i,
                "symbol": "NVDA",
            }
            for i in range(n)
        ]
    }


# ── Provider selection ───────────────────────────────────────────────────────

def test_get_provider_demo_mode_always_returns_fixture() -> None:
    s = Settings(use_demo_data=True)
    assert isinstance(_get_provider("stock", s), FixtureProvider)
    assert isinstance(_get_provider("crypto", s), FixtureProvider)


def test_get_provider_real_crypto_returns_coingecko() -> None:
    s = Settings(use_demo_data=False, coingecko_api_key="cg-key", marketstack_api_key="ms-key")
    assert isinstance(_get_provider("crypto", s), CoinGeckoProvider)


def test_get_provider_real_stock_returns_marketstack() -> None:
    s = Settings(use_demo_data=False, marketstack_api_key="ms-key", coingecko_api_key="cg-key")
    assert isinstance(_get_provider("stock", s), MarketstackProvider)


def test_get_provider_missing_coingecko_key_exits() -> None:
    s = Settings(use_demo_data=False, coingecko_api_key="", marketstack_api_key="ms-key")
    with pytest.raises(SystemExit) as exc:
        _get_provider("crypto", s)
    assert exc.value.code == 1


def test_get_provider_missing_marketstack_key_exits() -> None:
    s = Settings(use_demo_data=False, marketstack_api_key="", coingecko_api_key="cg-key")
    with pytest.raises(SystemExit) as exc:
        _get_provider("stock", s)
    assert exc.value.code == 1


# ── Ingestion DB persistence ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_coingecko_persists_rows(db, httpx_mock) -> None:
    httpx_mock.add_response(
        url=re.compile(r"https://api\.coingecko\.com/.*bitcoin.*"),
        json=_coingecko_response(63),
    )
    asset = (await db.execute(select(Asset).where(Asset.symbol == "BTC"))).scalar_one()
    provider = CoinGeckoProvider("test-key")
    await ingest_asset(db, asset, provider)

    count = (
        await db.execute(select(func.count()).where(DailyPrice.asset_id == asset.id))
    ).scalar()
    assert count > 0

    # Real provider → all rows must have is_demo=False
    demo_count = (
        await db.execute(
            select(func.count()).where(
                DailyPrice.asset_id == asset.id, DailyPrice.is_demo == True  # noqa: E712
            )
        )
    ).scalar()
    assert demo_count == 0


@pytest.mark.asyncio
async def test_ingest_marketstack_persists_rows(db, httpx_mock) -> None:
    httpx_mock.add_response(
        url=re.compile(r"https://api\.marketstack\.com/.*"),
        json=_marketstack_response(63),
    )
    asset = (await db.execute(select(Asset).where(Asset.symbol == "NVDA"))).scalar_one()
    provider = MarketstackProvider("test-key")
    await ingest_asset(db, asset, provider)

    count = (
        await db.execute(select(func.count()).where(DailyPrice.asset_id == asset.id))
    ).scalar()
    assert count > 0

    demo_count = (
        await db.execute(
            select(func.count()).where(
                DailyPrice.asset_id == asset.id, DailyPrice.is_demo == True  # noqa: E712
            )
        )
    ).scalar()
    assert demo_count == 0


@pytest.mark.asyncio
async def test_upsert_replaces_fixture_prices(db, httpx_mock) -> None:
    """Fixture rows (is_demo=True) must be replaced when real data is ingested."""
    asset = (await db.execute(select(Asset).where(Asset.symbol == "BTC"))).scalar_one()

    # Confirm fixture data is demo
    before = (
        await db.execute(
            select(DailyPrice.is_demo).where(DailyPrice.asset_id == asset.id).limit(1)
        )
    ).scalar()
    assert before is True

    httpx_mock.add_response(
        url=re.compile(r"https://api\.coingecko\.com/.*bitcoin.*"),
        json=_coingecko_response(63),
    )
    await ingest_asset(db, asset, CoinGeckoProvider("key"))

    demo_count = (
        await db.execute(
            select(func.count()).where(
                DailyPrice.asset_id == asset.id, DailyPrice.is_demo == True  # noqa: E712
            )
        )
    ).scalar()
    assert demo_count == 0


@pytest.mark.asyncio
async def test_seed_asset_catalogue_is_idempotent(db) -> None:
    count_before = (await db.execute(select(func.count()).select_from(Asset))).scalar()
    await seed_asset_catalogue(db)
    count_after = (await db.execute(select(func.count()).select_from(Asset))).scalar()
    assert count_before == count_after


# ── New data-integrity tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_real_ingest_deletes_all_fixture_rows(db, httpx_mock) -> None:
    """After real ingestion, zero fixture rows (is_demo=True) must remain — even dates not in the fetch."""
    asset = (await db.execute(select(Asset).where(Asset.symbol == "BTC"))).scalar_one()

    fixture_count = (
        await db.execute(
            select(func.count()).where(DailyPrice.asset_id == asset.id, DailyPrice.is_demo == True)  # noqa: E712
        )
    ).scalar()
    assert fixture_count > 0  # pre-condition: fixture rows exist

    # Use a date range offset by 5 days so some fixture dates are NOT covered by the real fetch.
    alt_start = _FIXTURE_START + timedelta(days=5)
    httpx_mock.add_response(
        url=re.compile(r"https://api\.coingecko\.com/.*bitcoin.*"),
        json={
            "prices": [
                [_ts_ms(alt_start + timedelta(days=i)), 60000.0 + i * 50]
                for i in range(MIN_OBSERVATIONS + 5)
            ]
        },
    )
    await ingest_asset(db, asset, CoinGeckoProvider("key"))

    # ALL fixture rows must be deleted — including dates absent from the real fetch.
    fixture_after = (
        await db.execute(
            select(func.count()).where(DailyPrice.asset_id == asset.id, DailyPrice.is_demo == True)  # noqa: E712
        )
    ).scalar()
    assert fixture_after == 0


@pytest.mark.asyncio
async def test_seed_asset_catalogue_partial(db) -> None:
    """seed_asset_catalogue must re-add an asset that was removed, without duplicating others."""
    btc = (await db.execute(select(Asset).where(Asset.symbol == "BTC"))).scalar_one()
    await db.delete(btc)
    await db.flush()

    count_without_btc = (await db.execute(select(func.count()).select_from(Asset))).scalar()
    await seed_asset_catalogue(db)
    count_after = (await db.execute(select(func.count()).select_from(Asset))).scalar()

    assert count_after == count_without_btc + 1
    assert (await db.execute(select(Asset).where(Asset.symbol == "BTC"))).scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_missing_key_prevents_any_db_write(db) -> None:
    """_get_provider exits with code 1 before any DB write when a required key is absent."""
    price_count_before = (await db.execute(select(func.count()).select_from(DailyPrice))).scalar()

    s = Settings(use_demo_data=False, marketstack_api_key="", coingecko_api_key="cg-key")
    with pytest.raises(SystemExit) as exc:
        _get_provider("stock", s)
    assert exc.value.code == 1

    price_count_after = (await db.execute(select(func.count()).select_from(DailyPrice))).scalar()
    assert price_count_after == price_count_before


@pytest.mark.asyncio
async def test_demo_true_when_any_price_row_is_fixture(client: AsyncClient, db, httpx_mock) -> None:
    """Correlation response must be demo=True when stock is real but crypto is still fixture."""
    nvda = (await db.execute(select(Asset).where(Asset.symbol == "NVDA"))).scalar_one()

    httpx_mock.add_response(
        url=re.compile(r"https://api\.marketstack\.com/.*"),
        json=_marketstack_response(63),
    )
    await ingest_asset(db, nvda, MarketstackProvider("ms-key"))

    # NVDA is now real (is_demo=False); all crypto assets are still fixture (is_demo=True).
    resp = await client.get("/api/v1/correlation/NVDA")
    assert resp.status_code == 200
    assert resp.json()["demo"] is True


@pytest.mark.asyncio
async def test_seed_fixture_data_is_idempotent(db) -> None:
    """Calling seed_fixture_data a second time must not change asset or price counts."""
    asset_count_before = (await db.execute(select(func.count()).select_from(Asset))).scalar()
    price_count_before = (await db.execute(select(func.count()).select_from(DailyPrice))).scalar()

    await seed_fixture_data(db)

    assert (await db.execute(select(func.count()).select_from(Asset))).scalar() == asset_count_before
    assert (await db.execute(select(func.count()).select_from(DailyPrice))).scalar() == price_count_before


# ── Real-mode end-to-end ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_real_mode_ingestion_then_correlation(client: AsyncClient, db, httpx_mock) -> None:
    """
    Ingest NVDA + BTC with real providers (mocked HTTP), remove all other crypto
    assets so the response only references those two, then verify demo=False.
    """
    from sqlalchemy import delete as sa_delete

    # Keep only BTC among crypto so every asset used in the response has real data.
    await db.execute(
        sa_delete(Asset).where(Asset.asset_type == "crypto", Asset.symbol != "BTC")
    )
    await db.commit()

    nvda = (await db.execute(select(Asset).where(Asset.symbol == "NVDA"))).scalar_one()
    btc = (await db.execute(select(Asset).where(Asset.symbol == "BTC"))).scalar_one()

    httpx_mock.add_response(
        url=re.compile(r"https://api\.marketstack\.com/.*"),
        json=_marketstack_response(63),
    )
    httpx_mock.add_response(
        url=re.compile(r"https://api\.coingecko\.com/.*bitcoin.*"),
        json=_coingecko_response(63),
    )

    await ingest_asset(db, nvda, MarketstackProvider("ms-key"))
    await ingest_asset(db, btc, CoinGeckoProvider("cg-key"))

    assets_resp = await client.get("/api/v1/assets")
    assert assets_resp.status_code == 200
    symbols = {a["symbol"] for a in assets_resp.json()["assets"]}
    assert "NVDA" in symbols
    assert "BTC" in symbols

    # Both NVDA and BTC are now real → demo must be False.
    corr_resp = await client.get("/api/v1/correlation/NVDA")
    assert corr_resp.status_code == 200
    body = corr_resp.json()
    assert body["demo"] is False
    assert len(body["scores"]) > 0
