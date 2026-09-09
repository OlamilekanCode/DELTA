"""Tests for /exposures, /graphs, and expanded /assets endpoints."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exposure_score import StoredExposureScore


@pytest.mark.asyncio
async def test_exposures_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/exposures/NVDA")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_exposures_schema(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/exposures/NVDA")
    body = resp.json()
    assert "stock" in body
    assert "scores" in body
    assert "demo" in body
    assert "stale" in body
    assert body["stock"]["symbol"] == "NVDA"


@pytest.mark.asyncio
async def test_exposures_scores_are_signed(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/exposures/NVDA")
    for s in resp.json()["scores"]:
        assert -1.0 <= s["score"] <= 1.0


@pytest.mark.asyncio
async def test_exposures_unknown_stock_404(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/exposures/FAKEX")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_exposures_demo_flag_true_for_fixture_data(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/exposures/NVDA")
    assert resp.json()["demo"] is True


@pytest.mark.asyncio
async def test_exposures_stale_reflects_data_ts_not_computed_at(client: AsyncClient, db: AsyncSession) -> None:
    """A score recomputed "now" (computed_at fresh) but built from old
    market data (data_ts stale) must report stale=True — recomputing
    against unchanged old prices must never look fresh just because the
    job happened to run."""
    old_ts = datetime.now(UTC) - timedelta(days=60)
    await db.execute(update(StoredExposureScore).values(computed_at=datetime.now(UTC), data_ts=old_ts))
    await db.commit()

    resp = await client.get("/api/v1/exposures/NVDA")
    assert resp.json()["stale"] is True


@pytest.mark.asyncio
async def test_graphs_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/graphs/NVDA")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_graphs_schema(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/graphs/NVDA")
    body = resp.json()
    assert "nodes" in body
    assert "edges" in body
    assert "stock" in body
    center_nodes = [n for n in body["nodes"] if n["is_center"]]
    assert len(center_nodes) == 1
    assert center_nodes[0]["symbol"] == "NVDA"


@pytest.mark.asyncio
async def test_graphs_edges_match_nodes(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/graphs/NVDA")
    body = resp.json()
    node_ids = {n["id"] for n in body["nodes"]}
    for edge in body["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids


@pytest.mark.asyncio
async def test_graphs_edge_direction_field(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/graphs/NVDA")
    for edge in resp.json()["edges"]:
        assert edge["direction"] in ("positive", "inverse")
        assert "score" in edge
        assert "weight" in edge
        assert edge["weight"] == round(abs(edge["score"]), 4)
        expected_dir = "positive" if edge["score"] >= 0 else "inverse"
        assert edge["direction"] == expected_dir


@pytest.mark.asyncio
async def test_graphs_min_score_invalid_returns_422(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/graphs/NVDA?min_score=1.5")).status_code == 422
    assert (await client.get("/api/v1/graphs/NVDA?min_score=-0.1")).status_code == 422


@pytest.mark.asyncio
async def test_graphs_unknown_stock_404(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/graphs/FAKEX")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_assets_search_by_symbol(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets/search?q=btc")
    assert resp.status_code == 200
    symbols = {a["symbol"] for a in resp.json()["assets"]}
    assert "BTC" in symbols


@pytest.mark.asyncio
async def test_assets_search_by_name(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets/search?q=bitcoin")
    assert resp.status_code == 200
    symbols = {a["symbol"] for a in resp.json()["assets"]}
    assert "BTC" in symbols


@pytest.mark.asyncio
async def test_assets_search_empty_returns_free_tier_only_for_guests(client: AsyncClient) -> None:
    """Guests must never see the full 120-asset catalogue — only the free tier."""
    resp = await client.get("/api/v1/assets/search")
    assert resp.status_code == 200
    assert len(resp.json()["assets"]) == 38  # 8 free stocks + 30 free crypto


@pytest.mark.asyncio
async def test_asset_detail_stock(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets/NVDA")
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "NVDA"
    assert body["asset_type"] == "stock"
    assert body["last_price"] is not None


@pytest.mark.asyncio
async def test_asset_detail_crypto(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets/BTC")
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "BTC"
    assert body["asset_type"] == "crypto"
    assert body["last_price"] is not None


@pytest.mark.asyncio
async def test_asset_detail_crypto_quote_is_demo(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets/BTC")
    body = resp.json()
    assert body["is_demo"] is True
    assert body["quote_provider"] == "fixture"


@pytest.mark.asyncio
async def test_asset_detail_404(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets/FAKEXYZ")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_asset_history_returns_prices(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets/NVDA/history")
    assert resp.status_code == 200
    body = resp.json()
    assert "prices" in body
    assert len(body["prices"]) > 0
    assert body["symbol"] == "NVDA"


@pytest.mark.asyncio
async def test_asset_history_prices_ascending(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets/BTC/history")
    prices = resp.json()["prices"]
    dates = [p["date"] for p in prices]
    assert dates == sorted(dates)


@pytest.mark.asyncio
async def test_asset_list_includes_last_price(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets")
    for asset in resp.json()["assets"]:
        assert asset["last_price"] is not None, f"{asset['symbol']} missing last_price"


@pytest.mark.asyncio
async def test_assets_search_type_filter(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets/search?type=stock")
    assert resp.status_code == 200
    for a in resp.json()["assets"]:
        assert a["asset_type"] == "stock"
