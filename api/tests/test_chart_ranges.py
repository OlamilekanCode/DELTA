import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.runner import seed_fixture_intraday_data


@pytest.mark.asyncio
async def test_history_range_3m_uses_daily_prices(client: AsyncClient) -> None:
    r = await client.get("/api/v1/assets/NVDA/history?range=3M")
    assert r.status_code == 200
    body = r.json()
    assert body["collecting_data"] is None
    assert all(p["ts"] is None for p in body["prices"])


@pytest.mark.asyncio
async def test_history_range_1y_uses_daily_prices(client: AsyncClient) -> None:
    r = await client.get("/api/v1/assets/NVDA/history?range=1Y")
    assert r.status_code == 200
    assert r.json()["collecting_data"] is None


@pytest.mark.asyncio
async def test_history_no_range_falls_back_to_days_param(client: AsyncClient) -> None:
    r = await client.get("/api/v1/assets/NVDA/history?days=30")
    assert r.status_code == 200
    assert len(r.json()["prices"]) <= 31  # cutoff is inclusive of both endpoints


@pytest.mark.asyncio
async def test_history_intraday_range_collecting_data_when_empty(client: AsyncClient) -> None:
    r = await client.get("/api/v1/assets/NVDA/history?range=1D")
    assert r.status_code == 200
    body = r.json()
    assert body["collecting_data"] is True
    assert body["prices"] == []


@pytest.mark.asyncio
async def test_history_intraday_range_ready_after_seeding(
    client: AsyncClient, db: AsyncSession
) -> None:
    await seed_fixture_intraday_data(db)
    r = await client.get("/api/v1/assets/NVDA/history?range=1D")
    assert r.status_code == 200
    body = r.json()
    assert body["collecting_data"] is False
    assert len(body["prices"]) == 13
    assert all(p["ts"] is not None for p in body["prices"])
    # ascending order
    timestamps = [p["ts"] for p in body["prices"]]
    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_history_unknown_symbol_404(client: AsyncClient) -> None:
    r = await client.get("/api/v1/assets/NOTASYMBOL/history?range=1D")
    assert r.status_code == 404
