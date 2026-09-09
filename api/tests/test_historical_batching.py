"""Tests for the historical refresh job's provider-call efficiency:

- Stock EOD refresh uses ONE batched Marketstack call for all symbols,
  never one sequential request per symbol.
- Crypto history refresh uses small bounded concurrency (CoinGecko has no
  batched historical-OHLCV endpoint) rather than a fully sequential loop —
  same call count, just not one at a time.
"""

import re
from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.ingestion import commands as commands_module
from app.ingestion.commands import cmd_refresh_crypto_history, cmd_refresh_stock_eod
from app.models.asset import Asset
from app.models.price import DailyPrice
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


def _eod_batch_response(symbols: list[str], as_of: date) -> dict:
    return {
        "data": [
            {"symbol": sym, "date": (as_of - timedelta(days=i)).isoformat(), "close": 100.0 + i, "adj_close": 100.0 + i}
            for sym in symbols
            for i in range(3)
        ]
    }


@pytest.mark.asyncio
async def test_cmd_refresh_stock_eod_uses_one_batch_call(db: AsyncSession, monkeypatch, httpx_mock) -> None:
    settings = _live_settings()
    monkeypatch.setattr(commands_module, "get_settings", lambda: settings)

    stock_result = await db.execute(select(Asset).where(Asset.asset_type == "stock"))
    stocks = stock_result.scalars().all()

    httpx_mock.add_response(
        url=re.compile(r"https://api\.marketstack\.com/v1/eod.*"),
        json=_eod_batch_response([s.symbol for s in stocks], date.today()),
    )

    counts = await cmd_refresh_stock_eod(skip_weekends=False)

    requests = [r for r in httpx_mock.get_requests() if "marketstack" in str(r.url)]
    assert len(requests) == 1  # one batch call for every stock symbol
    assert counts["requested"] == len(stocks)
    assert counts["succeeded"] == len(stocks)
    assert counts["records_written"] > 0

    price_count = (await db.execute(select(func.count()).select_from(DailyPrice))).scalar()
    assert price_count > 0


@pytest.mark.asyncio
async def test_cmd_refresh_stock_eod_preserves_data_on_batch_failure(db: AsyncSession, monkeypatch, httpx_mock) -> None:
    settings = _live_settings()
    monkeypatch.setattr(commands_module, "get_settings", lambda: settings)

    for _ in range(3):  # fetch_eod_batch retries up to 3 attempts before giving up
        httpx_mock.add_response(url=re.compile(r"https://api\.marketstack\.com/v1/eod.*"), status_code=500)

    price_count_before = (await db.execute(select(func.count()).select_from(DailyPrice))).scalar()
    counts = await cmd_refresh_stock_eod(skip_weekends=False)
    price_count_after = (await db.execute(select(func.count()).select_from(DailyPrice))).scalar()

    assert price_count_after == price_count_before  # existing data untouched
    assert counts["succeeded"] == 0
    assert counts["failed"] == counts["requested"]


@pytest.mark.asyncio
async def test_fetch_eod_batch_chunks_to_stay_under_marketstack_row_limit(httpx_mock) -> None:
    """20 symbols * 90-day window would need limit=2000 in one call —
    Marketstack's /eod `limit` caps at 1000 and silently truncates beyond
    it, so this must split into multiple calls that each stay under 1000."""
    provider = MarketstackProvider("ms-key")
    symbols = [f"SYM{i}" for i in range(20)]
    as_of = date.today()

    def _handle(request):
        qs = parse_qs(urlparse(str(request.url)).query)
        requested_symbols = qs["symbols"][0].split(",")
        assert int(qs["limit"][0]) <= 1000
        from httpx import Response
        return Response(
            200,
            json={
                "data": [
                    {"symbol": sym, "date": (as_of - timedelta(days=i)).isoformat(), "close": 100.0 + i, "adj_close": 100.0 + i}
                    for sym in requested_symbols
                    for i in range(3)
                ]
            },
        )

    httpx_mock.add_callback(_handle, url=re.compile(r"https://api\.marketstack\.com/v1/eod.*"))

    result = await provider.fetch_eod_batch(symbols, days=90)

    requests = [r for r in httpx_mock.get_requests() if "marketstack" in str(r.url)]
    assert len(requests) > 1  # split into multiple sub-1000 chunks
    assert set(result.keys()) == set(symbols)  # every symbol present, none dropped by chunking
    for sym in symbols:
        assert len(result[sym]) == 3


@pytest.mark.asyncio
@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
async def test_cmd_refresh_crypto_history_bounded_concurrency(db: AsyncSession, monkeypatch, httpx_mock) -> None:
    """Same total CoinGecko call count as a sequential loop (one per asset)
    — bounded concurrency changes execution overlap, not call volume."""
    settings = _live_settings()
    monkeypatch.setattr(commands_module, "get_settings", lambda: settings)

    crypto_result = await db.execute(select(Asset).where(Asset.asset_type == "crypto"))
    crypto_assets = crypto_result.scalars().all()

    httpx_mock.add_response(
        url=re.compile(r"https://api\.coingecko\.com/api/v3/coins/.*/market_chart.*"),
        json={"prices": [[1700000000000 + i * 86400000, 100.0 + i] for i in range(5)]},
    )

    counts = await cmd_refresh_crypto_history()

    coingecko_requests = [r for r in httpx_mock.get_requests() if "coingecko" in str(r.url)]
    assert len(coingecko_requests) == len(crypto_assets)
    assert counts["requested"] == len(crypto_assets)
    assert counts["succeeded"] == len(crypto_assets)
    assert counts["records_written"] > 0
