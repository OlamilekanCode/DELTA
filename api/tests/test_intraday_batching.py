"""Tests for the batched intraday provider-call design (section 4):

- One Marketstack call for every stock symbol, not one per symbol.
- Crypto candles are built entirely from stored crypto_quote_observations —
  the intraday job makes zero CoinGecko calls.
- The current/in-progress 30-minute bucket is never persisted.
- cmd_refresh_crypto_quotes persists a timestamped observation per asset.
"""

import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.ingestion import commands as commands_module
from app.ingestion.commands import cmd_refresh_crypto_quotes, cmd_refresh_intraday
from app.models.asset import Asset
from app.models.crypto_observation import CryptoQuoteObservation
from app.models.intraday_price import IntradayPrice
from app.providers.marketstack import MarketstackProvider


def _live_settings(**overrides) -> Settings:
    fields = dict(
        use_demo_data=False,
        marketstack_api_key="ms-key",
        coingecko_api_key="cg-key",
        database_url="sqlite+aiosqlite:///./test.db",
    )
    fields.update(overrides)
    return Settings(**fields)


def _marketstack_intraday_response(symbols: list[str], bucket_ts: datetime) -> dict:
    return {
        "data": [
            {
                "symbol": sym,
                "date": bucket_ts.isoformat().replace("+00:00", "Z"),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
            }
            for sym in symbols
        ]
    }


@pytest.mark.asyncio
async def test_fetch_intraday_candles_batch_makes_one_request(httpx_mock) -> None:
    symbols = ["NVDA", "TSLA", "AMD"]
    bucket_ts = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) - timedelta(minutes=30)
    httpx_mock.add_response(
        url=re.compile(r"https://api\.marketstack\.com/v1/intraday.*"),
        json=_marketstack_intraday_response(symbols, bucket_ts),
    )
    provider = MarketstackProvider("ms-key")
    result = await provider.fetch_intraday_candles_batch(symbols)

    requests = httpx_mock.get_requests()
    assert len(requests) == 1  # exactly one HTTP call for all three symbols
    assert set(result.keys()) == set(symbols)
    for sym in symbols:
        assert len(result[sym]) == 1
        assert result[sym][0].close == 100.5


@pytest.mark.asyncio
async def test_cmd_refresh_intraday_makes_no_coingecko_calls(db: AsyncSession, monkeypatch, httpx_mock) -> None:
    """Crypto candles must come from stored observations only — zero CoinGecko HTTP calls."""
    settings = _live_settings()
    monkeypatch.setattr(commands_module, "get_settings", lambda: settings)

    # Force market-open status regardless of wall-clock time.
    import app.services.market_calendar as mc

    def fake_status(now=None):
        ts = now or datetime.now(UTC)
        bucket = ts.replace(minute=(ts.minute // 30) * 30, second=0, microsecond=0)
        return mc.MarketStatus(
            is_open=True, timezone=mc.MARKET_TIMEZONE, last_close=ts - timedelta(hours=6),
            next_open=ts + timedelta(hours=18), current_bucket=bucket, status_reason="test",
        )

    monkeypatch.setattr(mc, "get_market_status", fake_status)

    stock_result = await db.execute(select(Asset).where(Asset.asset_type == "stock"))
    stocks = stock_result.scalars().all()
    crypto_result = await db.execute(select(Asset).where(Asset.asset_type == "crypto"))
    crypto_assets = crypto_result.scalars().all()

    now = datetime.now(UTC)
    completed_bucket = now.replace(minute=(now.minute // 30) * 30, second=0, microsecond=0) - timedelta(minutes=30)
    for asset in crypto_assets:
        db.add(CryptoQuoteObservation(asset_id=asset.id, ts=completed_bucket + timedelta(minutes=5), price_usd=100.0, is_demo=False))
        db.add(CryptoQuoteObservation(asset_id=asset.id, ts=completed_bucket + timedelta(minutes=15), price_usd=101.0, is_demo=False))
    await db.commit()

    httpx_mock.add_response(
        url=re.compile(r"https://api\.marketstack\.com/v1/intraday.*"),
        json=_marketstack_intraday_response([s.symbol for s in stocks], completed_bucket),
    )

    await cmd_refresh_intraday()

    for req in httpx_mock.get_requests():
        assert "coingecko" not in str(req.url), f"Unexpected CoinGecko call: {req.url}"

    crypto_candle_count = (
        await db.execute(select(func.count()).select_from(IntradayPrice).where(IntradayPrice.provider == "coingecko"))
    ).scalar()
    assert crypto_candle_count > 0


@pytest.mark.asyncio
async def test_cmd_refresh_intraday_excludes_in_progress_bucket(db: AsyncSession, monkeypatch, httpx_mock) -> None:
    settings = _live_settings()
    monkeypatch.setattr(commands_module, "get_settings", lambda: settings)

    import app.services.market_calendar as mc

    def fake_status(now=None):
        ts = now or datetime.now(UTC)
        bucket = ts.replace(minute=(ts.minute // 30) * 30, second=0, microsecond=0)
        return mc.MarketStatus(
            is_open=True, timezone=mc.MARKET_TIMEZONE, last_close=ts - timedelta(hours=6),
            next_open=ts + timedelta(hours=18), current_bucket=bucket, status_reason="test",
        )

    monkeypatch.setattr(mc, "get_market_status", fake_status)

    stock_result = await db.execute(select(Asset).where(Asset.asset_type == "stock"))
    stocks = stock_result.scalars().all()
    crypto_result = await db.execute(select(Asset).where(Asset.asset_type == "crypto"))
    crypto_assets = crypto_result.scalars().all()

    now = datetime.now(UTC)
    in_progress_bucket = now.replace(minute=(now.minute // 30) * 30, second=0, microsecond=0)
    for asset in crypto_assets[:3]:
        db.add(CryptoQuoteObservation(asset_id=asset.id, ts=in_progress_bucket + timedelta(minutes=1), price_usd=100.0, is_demo=False))
    await db.commit()

    httpx_mock.add_response(
        url=re.compile(r"https://api\.marketstack\.com/v1/intraday.*"),
        json=_marketstack_intraday_response([s.symbol for s in stocks], in_progress_bucket),
    )

    await cmd_refresh_intraday()

    rows = (
        await db.execute(
            select(IntradayPrice).where(
                IntradayPrice.asset_id == crypto_assets[0].id, IntradayPrice.bucket_ts == in_progress_bucket
            )
        )
    ).scalars().all()
    assert rows == [], "the current in-progress bucket must never be persisted"


@pytest.mark.asyncio
async def test_cmd_refresh_intraday_marks_marketstack_failed_on_error(db: AsyncSession, monkeypatch, httpx_mock) -> None:
    """A completely failed Marketstack batch call must be visible in the
    returned counts, not hidden behind whatever crypto candles happened to
    build successfully from stored observations."""
    settings = _live_settings()
    monkeypatch.setattr(commands_module, "get_settings", lambda: settings)

    import app.services.market_calendar as mc

    def fake_status(now=None):
        ts = now or datetime.now(UTC)
        bucket = ts.replace(minute=(ts.minute // 30) * 30, second=0, microsecond=0)
        return mc.MarketStatus(
            is_open=True, timezone=mc.MARKET_TIMEZONE, last_close=ts - timedelta(hours=6),
            next_open=ts + timedelta(hours=18), current_bucket=bucket, status_reason="test",
        )

    monkeypatch.setattr(mc, "get_market_status", fake_status)

    # fetch_intraday_candles_batch retries on failure (stop_after_attempt(3))
    # before finally re-raising — register a failing response for each attempt.
    for _ in range(3):
        httpx_mock.add_response(
            url=re.compile(r"https://api\.marketstack\.com/v1/intraday.*"),
            status_code=500,
        )

    counts = await cmd_refresh_intraday()
    assert counts["marketstack_failed"] is True
    assert counts["score_stocks_recomputed"] == 0  # no stock candle data exists to score at all


@pytest.mark.asyncio
async def test_cmd_refresh_crypto_quotes_persists_observations(db: AsyncSession, monkeypatch, httpx_mock) -> None:
    settings = _live_settings()
    monkeypatch.setattr(commands_module, "get_settings", lambda: settings)

    crypto_result = await db.execute(select(Asset).where(Asset.asset_type == "crypto"))
    crypto_assets = crypto_result.scalars().all()

    httpx_mock.add_response(
        url=re.compile(r"https://api\.coingecko\.com/api/v3/coins/markets.*"),
        json=[
            {"symbol": a.symbol.lower(), "current_price": 100.0, "market_cap": 1e9,
             "total_volume": 1e6, "price_change_percentage_24h": 1.0}
            for a in crypto_assets
        ],
    )

    counts = await cmd_refresh_crypto_quotes()
    assert counts["requested"] == len(crypto_assets)
    assert counts["succeeded"] == len(crypto_assets)

    obs_count = (
        await db.execute(select(func.count()).select_from(CryptoQuoteObservation))
    ).scalar()
    assert obs_count == len(crypto_assets)

    requests = [r for r in httpx_mock.get_requests() if "coingecko" in str(r.url)]
    assert len(requests) == 1  # one batch call for every crypto asset
