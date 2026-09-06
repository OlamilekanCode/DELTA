"""Tests for the full 8-stock + 30-crypto asset catalogue."""

from datetime import date, timedelta

import pytest

from app.providers.fixtures import FIXTURE_ASSETS, FixtureProvider

EXPECTED_STOCKS = {"NVDA", "TSLA", "COIN", "MSTR", "AMD", "MSFT", "META", "PLTR"}
EXPECTED_CRYPTO = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOT", "NEAR", "ICP",
    "APT", "SUI", "HBAR", "ARB", "OP", "POL", "UNI", "AAVE", "INJ", "LINK",
    "GRT", "TAO", "RENDER", "FET", "AKT", "AIOZ", "FIL", "AR", "DOGE", "PEPE",
}
VALID_CATEGORIES = {
    "Layer 1", "Layer 2", "DeFi", "Oracle/Data",
    "AI/Compute", "Storage", "Memecoin", "Technology", "Finance",
}
STABLECOINS = {"USDT", "USDC", "DAI", "BUSD", "TUSD", "USDE", "FRAX"}


def test_fixture_has_8_stocks() -> None:
    stocks = [a for a in FIXTURE_ASSETS if a["asset_type"] == "stock"]
    assert len(stocks) == 8
    assert {a["symbol"] for a in stocks} == EXPECTED_STOCKS


def test_fixture_has_30_crypto() -> None:
    crypto = [a for a in FIXTURE_ASSETS if a["asset_type"] == "crypto"]
    assert len(crypto) == 30
    assert {a["symbol"] for a in crypto} == EXPECTED_CRYPTO


def test_all_crypto_have_coingecko_id() -> None:
    for a in FIXTURE_ASSETS:
        if a["asset_type"] == "crypto":
            assert a.get("coingecko_id"), f"{a['symbol']} is missing coingecko_id"


def test_stocks_have_no_coingecko_id() -> None:
    for a in FIXTURE_ASSETS:
        if a["asset_type"] == "stock":
            assert a.get("coingecko_id") is None, f"{a['symbol']} should not have coingecko_id"


def test_no_stablecoins() -> None:
    symbols = {a["symbol"] for a in FIXTURE_ASSETS}
    assert not (symbols & STABLECOINS), f"Stablecoin found: {symbols & STABLECOINS}"


def test_crypto_categories_valid() -> None:
    for a in FIXTURE_ASSETS:
        if a["asset_type"] == "crypto":
            assert a["category"] in VALID_CATEGORIES, (
                f"{a['symbol']} has invalid category {a['category']!r}"
            )


def test_no_duplicate_symbols() -> None:
    symbols = [a["symbol"] for a in FIXTURE_ASSETS]
    assert len(symbols) == len(set(symbols)), "Duplicate symbols found"


def test_no_duplicate_coingecko_ids() -> None:
    ids = [a["coingecko_id"] for a in FIXTURE_ASSETS if a.get("coingecko_id")]
    assert len(ids) == len(set(ids)), "Duplicate coingecko_ids found"


@pytest.mark.asyncio
async def test_fixture_provider_has_data_for_all_assets() -> None:
    provider = FixtureProvider()
    for asset in FIXTURE_ASSETS:
        rows = await provider.fetch_ohlcv(asset["symbol"], 90)
        assert len(rows) > 0, f"No fixture data for {asset['symbol']}"
        assert all(r.close > 0 for r in rows), f"Non-positive close for {asset['symbol']}"


@pytest.mark.asyncio
async def test_fixture_provider_pepe_has_small_positive_price() -> None:
    provider = FixtureProvider()
    rows = await provider.fetch_ohlcv("PEPE", 90)
    assert len(rows) > 0
    assert all(0 < r.close < 1 for r in rows), "PEPE price should be a small positive value"


@pytest.mark.asyncio
async def test_fixture_dates_are_relative_to_today() -> None:
    """Fixture dates must always end near today, never be hardcoded."""
    provider = FixtureProvider()
    rows = await provider.fetch_ohlcv("BTC", 90)
    today = date.today()
    last_date = date.fromisoformat(rows[-1].date)
    assert last_date >= today - timedelta(days=2), (
        f"Last fixture date {last_date} is stale — fixture dates must be relative to today"
    )
    assert last_date <= today, f"Last fixture date {last_date} is in the future"


@pytest.mark.asyncio
async def test_fixture_quotes_have_all_crypto() -> None:
    """FixtureProvider.fetch_quotes must return a quote for every crypto asset."""
    provider = FixtureProvider()
    crypto_symbols = [a["symbol"] for a in FIXTURE_ASSETS if a["asset_type"] == "crypto"]
    quotes = await provider.fetch_quotes(crypto_symbols)
    returned = {q.symbol for q in quotes}
    assert returned == set(crypto_symbols), f"Missing quotes for: {set(crypto_symbols) - returned}"


@pytest.mark.asyncio
async def test_fixture_quotes_have_valid_fields() -> None:
    provider = FixtureProvider()
    quotes = await provider.fetch_quotes(["BTC", "ETH"])
    for q in quotes:
        assert q.price_usd > 0
        assert q.market_cap_usd is not None and q.market_cap_usd > 0
        assert q.volume_24h_usd is not None and q.volume_24h_usd > 0
        assert q.change_24h_pct is not None
        assert -100 < q.change_24h_pct < 100
