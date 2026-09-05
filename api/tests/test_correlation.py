import math

import pytest
from httpx import AsyncClient

from app.services.correlation import (
    MIN_OBSERVATIONS,
    PricePoint,
    align_series,
    compute_exposure_scores,
    log_returns,
    normalize_base100,
    pearson_r,
)

# ── Unit tests ─────────────────────────────────────────────────────────────

def test_log_returns_basic() -> None:
    prices = [100.0, 110.0, 121.0]
    rets = log_returns(prices)
    assert len(rets) == 2
    assert math.isclose(rets[0], math.log(110 / 100), rel_tol=1e-9)


def test_log_returns_too_short() -> None:
    assert log_returns([100.0]) == []
    assert log_returns([]) == []


def test_pearson_r_perfect_correlation() -> None:
    xs = list(range(1, 50))
    ys = [x * 2.0 for x in xs]
    r, n = pearson_r(xs, ys)
    assert math.isclose(r, 1.0, abs_tol=1e-9)
    assert n == 49


def test_pearson_r_insufficient_observations() -> None:
    xs = list(range(1, 10))  # only 9 — below MIN_OBSERVATIONS
    ys = list(range(1, 10))
    r, n = pearson_r(xs, ys)
    assert r == 0.0
    assert n == 9


def test_normalize_base100() -> None:
    prices = [50.0, 100.0, 75.0]
    norm = normalize_base100(prices)
    assert norm[0] == 100.0
    assert norm[1] == 200.0
    assert norm[2] == 150.0


def test_align_series_basic() -> None:
    a = [PricePoint("2026-01-01", 100.0), PricePoint("2026-01-02", 110.0), PricePoint("2026-01-03", 105.0)]
    b = [PricePoint("2026-01-01", 200.0), PricePoint("2026-01-03", 210.0)]
    xa, _, dates = align_series(a, b)
    assert len(xa) == 2
    assert dates == ["2026-01-01", "2026-01-03"]


def test_compute_scores_aligns_before_log_returns() -> None:
    # Stock: weekdays only (Mon–Fri over 10 weeks = 50 days → 49 returns after alignment)
    # Crypto: every day including weekends
    import datetime

    start = datetime.date(2026, 1, 5)  # Monday
    stock_prices: list[PricePoint] = []
    crypto_prices: list[PricePoint] = []
    price = 100.0
    crypto_price = 50000.0
    day = start
    for _ in range(70):  # 10 weeks of calendar days
        if day.weekday() < 5:  # weekday
            stock_prices.append(PricePoint(day.isoformat(), round(price, 4)))
            price *= 1.001
        crypto_prices.append(PricePoint(day.isoformat(), round(crypto_price, 4)))
        crypto_price *= 1.0005
        day += datetime.timedelta(days=1)

    crypto_map = {"BTC": ("Bitcoin", "BTC Ecosystem", crypto_prices)}
    scores = compute_exposure_scores(stock_prices, crypto_map)

    assert len(scores) == 1
    s = scores[0]
    # Observations must equal weekday pairs only (common dates - 1)
    common_count = sum(1 for p in stock_prices if any(c.date == p.date for c in crypto_prices))
    assert s.observations == common_count - 1
    assert s.observations >= MIN_OBSERVATIONS


def test_compute_scores_with_missing_dates() -> None:
    # Both series share dates except one gap in the middle for crypto
    stock = [PricePoint(f"2026-01-{d:02d}", float(100 + d)) for d in range(1, 60)]
    # Crypto missing Jan 15
    crypto = [PricePoint(f"2026-01-{d:02d}", float(200 + d)) for d in range(1, 60) if d != 15]

    scores = compute_exposure_scores(stock, {"ETH": ("Ethereum", "DeFi", crypto)})

    assert len(scores) == 1
    # The gap date is excluded from common_dates → observations = (58 common dates) - 1 = 57
    assert scores[0].observations == 57


# ── Integration tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_correlation_endpoint_returns_200(client: AsyncClient) -> None:
    r = await client.get("/api/v1/correlation/NVDA")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_correlation_endpoint_schema(client: AsyncClient) -> None:
    r = await client.get("/api/v1/correlation/NVDA")
    body = r.json()
    assert body["stock"]["symbol"] == "NVDA"
    assert isinstance(body["scores"], list)
    assert len(body["scores"]) > 0
    assert isinstance(body["price_series"]["stock"], list)
    assert body["demo"] is True


@pytest.mark.asyncio
async def test_correlation_scores_are_non_negative(client: AsyncClient) -> None:
    r = await client.get("/api/v1/correlation/NVDA")
    for score in r.json()["scores"]:
        assert score["score"] >= 0.0


@pytest.mark.asyncio
async def test_correlation_unknown_symbol_returns_404(client: AsyncClient) -> None:
    r = await client.get("/api/v1/correlation/FAKE")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_correlation_days_too_small(client: AsyncClient) -> None:
    r = await client.get("/api/v1/correlation/NVDA?days=10")
    assert r.status_code == 422  # FastAPI Query validation


@pytest.mark.asyncio
async def test_correlation_days_too_large(client: AsyncClient) -> None:
    r = await client.get("/api/v1/correlation/NVDA?days=200")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_assets_endpoint(client: AsyncClient) -> None:
    r = await client.get("/api/v1/assets")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["assets"], list)
    symbols = {a["symbol"] for a in body["assets"]}
    assert "NVDA" in symbols
    assert "BTC" in symbols


@pytest.mark.asyncio
async def test_assets_filter_crypto(client: AsyncClient) -> None:
    r = await client.get("/api/v1/assets?type=crypto")
    assert r.status_code == 200
    for asset in r.json()["assets"]:
        assert asset["asset_type"] == "crypto"
