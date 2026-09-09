"""GET /api/v1/graphs/{symbol}?interval=live — live (intraday) graph mode."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.runner import seed_fixture_intraday_data


@pytest.mark.asyncio
async def test_graph_live_ready(client: AsyncClient, db: AsyncSession) -> None:
    await seed_fixture_intraday_data(db)
    r = await client.get("/api/v1/graphs/NVDA?interval=live")
    assert r.status_code == 200
    body = r.json()
    assert body["interval"] == "live"
    assert body["status"] == "ready"
    assert body["nodes"][0]["is_center"] is True
    assert body["nodes"][0]["symbol"] == "NVDA"
    for edge in body["edges"]:
        assert -1.0 <= edge["score"] <= 1.0
        assert edge["weight"] == round(abs(edge["score"]), 4)
        assert edge["direction"] in ("positive", "inverse")


@pytest.mark.asyncio
async def test_graph_live_collecting_data_when_no_intraday_scores(client: AsyncClient) -> None:
    r = await client.get("/api/v1/graphs/NVDA?interval=live")
    assert r.status_code == 200
    body = r.json()
    assert body["interval"] == "live"
    assert body["status"] == "collecting_data"
    assert body["edges"] == []
    assert body["required_count"] is not None


@pytest.mark.asyncio
async def test_graph_historical_default_unaffected(client: AsyncClient) -> None:
    r = await client.get("/api/v1/graphs/NVDA")
    assert r.status_code == 200
    body = r.json()
    assert body["interval"] == "historical"
    assert body["status"] == "ready"


@pytest.mark.asyncio
async def test_graph_live_unknown_symbol_404(client: AsyncClient) -> None:
    r = await client.get("/api/v1/graphs/NOTASYMBOL?interval=live")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_graph_invalid_interval_422(client: AsyncClient) -> None:
    r = await client.get("/api/v1/graphs/NVDA?interval=bogus")
    assert r.status_code == 422
