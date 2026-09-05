import math

import pytest
from httpx import AsyncClient

from app.services.correlation import (
    PricePoint,
    align_series,
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
    xa, xb, dates = align_series(a, b)
    assert len(xa) == 2
    assert dates == ["2026-01-01", "2026-01-03"]


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
