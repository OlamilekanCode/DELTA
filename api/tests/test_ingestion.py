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
from app.ingestion.runner import _get_provider, ingest_asset, seed_asset_catalogue
from app.models.asset import Asset
from app.models.price import DailyPrice
from app.providers.coingecko import CoinGeckoProvider
from app.providers.fixtures import FixtureProvider
from app.providers.marketstack import MarketstackProvider

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


# ── Real-mode end-to-end ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_real_mode_ingestion_then_correlation(client: AsyncClient, db, httpx_mock) -> None:
    """
    Ingest NVDA (mocked Marketstack) and BTC (mocked CoinGecko), then verify
    the correlation endpoint returns demo=False and non-empty scores.
    """
    nvda = (await db.execute(select(Asset).where(Asset.symbol == "NVDA"))).scalar_one()
    btc = (await db.execute(select(Asset).where(Asset.symbol == "BTC"))).scalar_one()

    # Only register mocks for the two assets we actually ingest
    httpx_mock.add_response(
        url=re.compile(r"https://api\.marketstack\.com/.*"),
        json=_marketstack_response(63),
    )
    httpx_mock.add_response(
        url=re.compile(r"https://api\.coingecko\.com/.*bitcoin.*"),
        json=_coingecko_response(63),
    )

    # Ingest NVDA (stock) and BTC (crypto) with mocked real providers
    await ingest_asset(db, nvda, MarketstackProvider("ms-key"))
    await ingest_asset(db, btc, CoinGeckoProvider("cg-key"))

    # Assets endpoint must list assets
    assets_resp = await client.get("/api/v1/assets")
    assert assets_resp.status_code == 200
    symbols = {a["symbol"] for a in assets_resp.json()["assets"]}
    assert "NVDA" in symbols
    assert "BTC" in symbols

    # Correlation endpoint must reflect real data (demo=False) for NVDA
    corr_resp = await client.get("/api/v1/correlation/NVDA")
    assert corr_resp.status_code == 200
    body = corr_resp.json()
    assert body["demo"] is False
    assert len(body["scores"]) > 0
