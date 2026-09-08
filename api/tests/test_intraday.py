from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.runner import seed_fixture_intraday_data
from app.models.asset import Asset
from app.services.intraday import (
    MIN_INTRADAY_OBS,
    MIN_SAMPLE_COUNT,
    IntradayObservation,
    build_30min_candles,
    compute_intraday_scores,
)


def test_build_30min_candles_groups_and_aggregates() -> None:
    base = datetime(2026, 9, 8, 13, 30, tzinfo=UTC)
    observations = [
        IntradayObservation(ts=base, price=100.0),
        IntradayObservation(ts=base + timedelta(minutes=5), price=102.0),
        IntradayObservation(ts=base + timedelta(minutes=10), price=99.0),
        IntradayObservation(ts=base + timedelta(minutes=35), price=101.0),
    ]
    candles = build_30min_candles(observations)
    assert len(candles) == 2
    first = candles[0]
    assert first.open == 100.0
    assert first.high == 102.0
    assert first.low == 99.0
    assert first.close == 99.0
    assert first.sample_count == 3
    assert first.data_quality == "ok"

    second = candles[1]
    assert second.sample_count == 1
    assert second.data_quality == "reduced"  # below MIN_SAMPLE_COUNT


def test_build_30min_candles_rejects_non_positive_prices() -> None:
    base = datetime(2026, 9, 8, 13, 30, tzinfo=UTC)
    observations = [
        IntradayObservation(ts=base, price=0.0),
        IntradayObservation(ts=base, price=-5.0),
        IntradayObservation(ts=base, price=100.0),
    ]
    candles = build_30min_candles(observations)
    assert len(candles) == 1
    assert candles[0].sample_count == 1


def test_build_30min_candles_min_sample_count_override() -> None:
    base = datetime(2026, 9, 8, 13, 30, tzinfo=UTC)
    observations = [IntradayObservation(ts=base, price=100.0)]
    candles = build_30min_candles(observations, min_sample_count=1)
    assert candles[0].data_quality == "ok"


@pytest.mark.asyncio
async def test_intraday_endpoint_demo_mode_ready(client: AsyncClient, db: AsyncSession) -> None:
    await seed_fixture_intraday_data(db)
    r = await client.get("/api/v1/intraday/NVDA")
    assert r.status_code == 200
    body = r.json()
    assert body["stock"]["symbol"] == "NVDA"
    assert body["status"] == "ready"
    assert body["demo"] is True
    assert body["interval"] == "30m"
    assert isinstance(body["scores"], list)
    for s in body["scores"]:
        assert -1.0 <= s["score"] <= 1.0
        assert s["observations"] >= MIN_INTRADAY_OBS


@pytest.mark.asyncio
async def test_intraday_endpoint_unknown_symbol_404(client: AsyncClient) -> None:
    r = await client.get("/api/v1/intraday/NOTASYMBOL")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_compute_intraday_scores_collecting_data_when_no_candles(db: AsyncSession) -> None:
    stock_result = await db.execute(
        select(Asset).where(Asset.symbol == "NVDA", Asset.asset_type == "stock")
    )
    stock = stock_result.scalar_one()
    results, count = await compute_intraday_scores(db, stock, [])
    assert results == []
    assert count >= 0


def test_min_sample_count_constant() -> None:
    assert MIN_SAMPLE_COUNT == 3
