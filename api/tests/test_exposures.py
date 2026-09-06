"""Tests for /exposures, /graphs, and expanded /assets endpoints."""

import pytest
from httpx import AsyncClient


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
async def test_exposures_scores_non_negative(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/exposures/NVDA")
    for s in resp.json()["scores"]:
        assert s["score"] >= 0.0


@pytest.mark.asyncio
async def test_exposures_unknown_stock_404(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/exposures/FAKEX")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_exposures_demo_flag_true_for_fixture_data(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/exposures/NVDA")
    assert resp.json()["demo"] is True


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
async def test_assets_search_empty_returns_all(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets/search")
    assert resp.status_code == 200
    assert len(resp.json()["assets"]) == 38  # 8 stocks + 30 crypto


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
