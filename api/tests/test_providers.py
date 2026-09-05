import pytest

from app.providers.base import PriceRow
from app.providers.fixtures import FixtureProvider


@pytest.mark.asyncio
async def test_fixture_provider_returns_price_rows() -> None:
    provider = FixtureProvider()
    rows = await provider.fetch_ohlcv("NVDA", 90)
    assert len(rows) > 0
    assert all(isinstance(r, PriceRow) for r in rows)


@pytest.mark.asyncio
async def test_fixture_provider_row_shape() -> None:
    provider = FixtureProvider()
    rows = await provider.fetch_ohlcv("BTC", 90)
    assert len(rows) > 0
    first = rows[0]
    assert isinstance(first.date, str)
    assert len(first.date) == 10  # "YYYY-MM-DD"
    assert isinstance(first.close, float)
    assert first.close > 0


@pytest.mark.asyncio
async def test_fixture_provider_respects_days_limit() -> None:
    provider = FixtureProvider()
    rows = await provider.fetch_ohlcv("ETH", 30)
    assert len(rows) <= 30


@pytest.mark.asyncio
async def test_fixture_provider_unknown_symbol_returns_empty() -> None:
    provider = FixtureProvider()
    rows = await provider.fetch_ohlcv("UNKNOWN", 90)
    assert rows == []
