from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.runner import seed_fixture_intraday_data
from app.models.asset import Asset
from app.models.intraday_exposure_score import IntradayExposureScore
from app.services.intraday import (
    MIN_INTRADAY_OBS,
    MIN_SAMPLE_COUNT,
    IntradayCandle,
    IntradayObservation,
    build_30min_candles,
    compute_intraday_scores,
    floor_to_bucket,
    ingest_intraday_candles,
    recompute_intraday_scores_for_stock,
)


def _full_candles(base: datetime, n: int, start_price: float = 100.0, step: float = 0.1) -> list[IntradayCandle]:
    return [
        IntradayCandle(
            bucket_ts=base + timedelta(minutes=30 * i), open=start_price, high=start_price + 1,
            low=start_price - 1, close=start_price + i * step, sample_count=5, data_quality="ok",
        )
        for i in range(n)
    ]


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


@pytest.mark.asyncio
async def test_intraday_endpoint_never_computes_scores(client: AsyncClient, db: AsyncSession) -> None:
    """GET /intraday must only read stored IntradayExposureScore rows —
    the router intentionally never imports compute_intraday_scores."""
    await seed_fixture_intraday_data(db)

    import app.routers.intraday as intraday_router

    assert not hasattr(intraday_router, "compute_intraday_scores")

    r = await client.get("/api/v1/intraday/NVDA")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["data_ts"] is not None
    assert body["freshness"] in ("fresh", "stale", "market_closed")


@pytest.mark.asyncio
async def test_intraday_endpoint_reduced_quality_excluded_from_scoring(db: AsyncSession) -> None:
    """A crypto with only reduced-quality candles must never contribute a score."""
    from datetime import UTC, datetime, timedelta

    from app.services.intraday import MIN_INTRADAY_OBS, IntradayCandle, ingest_intraday_candles

    stock_result = await db.execute(select(Asset).where(Asset.symbol == "NVDA", Asset.asset_type == "stock"))
    stock = stock_result.scalar_one()
    crypto_result = await db.execute(select(Asset).where(Asset.symbol == "BTC"))
    crypto = crypto_result.scalar_one()

    # Relative to "now" — _load_intraday_open_close cuts off data older than
    # MAX_SESSIONS * 3 days, so a hardcoded date would fall outside the window.
    base = (datetime.now(UTC) - timedelta(days=2)).replace(minute=0, second=0, microsecond=0)
    stock_candles = [
        IntradayCandle(
            bucket_ts=base + timedelta(minutes=30 * i), open=100.0, high=101.0, low=99.0,
            close=100.0 + i * 0.1, sample_count=5, data_quality="ok",
        )
        for i in range(MIN_INTRADAY_OBS + 5)
    ]
    # Crypto candles exist for the same buckets but are all reduced quality.
    crypto_candles = [
        IntradayCandle(
            bucket_ts=base + timedelta(minutes=30 * i), open=50000.0, high=50100.0, low=49900.0,
            close=50000.0 + i * 10, sample_count=1, data_quality="reduced",
        )
        for i in range(MIN_INTRADAY_OBS + 5)
    ]
    await ingest_intraday_candles(db, stock.id, stock_candles, provider="test", is_demo=True)
    await ingest_intraday_candles(db, crypto.id, crypto_candles, provider="test", is_demo=True)
    await db.commit()

    results, count = await compute_intraday_scores(db, stock, [crypto])
    assert results[0].collecting_data is True
    assert results[0].observations == 0


def test_floor_to_bucket_normalises_naive_and_non_utc_timestamps() -> None:
    from datetime import timezone

    naive = datetime(2026, 9, 8, 13, 47, 12)
    assert floor_to_bucket(naive) == datetime(2026, 9, 8, 13, 30, tzinfo=UTC)

    minus_four = datetime(2026, 9, 8, 9, 47, 12, tzinfo=timezone(timedelta(hours=-4)))  # 13:47 UTC
    assert floor_to_bucket(minus_four) == datetime(2026, 9, 8, 13, 30, tzinfo=UTC)


@pytest.mark.asyncio
async def test_recompute_stores_collecting_data_pairs_not_just_ready(db: AsyncSession) -> None:
    """Every crypto pair gets a stored row — even one still below the
    alignment threshold — so GET /intraday can report progress without
    recomputing anything."""
    stock = (await db.execute(select(Asset).where(Asset.symbol == "NVDA", Asset.asset_type == "stock"))).scalar_one()
    ready_crypto = (await db.execute(select(Asset).where(Asset.symbol == "BTC"))).scalar_one()
    collecting_crypto = (await db.execute(select(Asset).where(Asset.symbol == "ETH"))).scalar_one()

    base = (datetime.now(UTC) - timedelta(days=2)).replace(minute=0, second=0, microsecond=0)
    full = _full_candles(base, MIN_INTRADAY_OBS + 5)
    await ingest_intraday_candles(db, stock.id, full, provider="test", is_demo=False)
    await ingest_intraday_candles(db, ready_crypto.id, full, provider="test", is_demo=False)
    await ingest_intraday_candles(db, collecting_crypto.id, full[:5], provider="test", is_demo=False)
    await db.commit()

    await recompute_intraday_scores_for_stock(db, stock, [ready_crypto, collecting_crypto])

    rows = (await db.execute(
        select(IntradayExposureScore).where(IntradayExposureScore.stock_id == stock.id)
    )).scalars().all()
    by_crypto = {r.crypto_id: r for r in rows}
    assert set(by_crypto) == {ready_crypto.id, collecting_crypto.id}
    assert by_crypto[ready_crypto.id].data_quality == "ok"
    assert by_crypto[collecting_crypto.id].data_quality == "collecting_data"
    assert by_crypto[collecting_crypto.id].observations == 5


@pytest.mark.asyncio
async def test_recompute_data_ts_is_last_common_candle_not_wall_clock(db: AsyncSession) -> None:
    stock = (await db.execute(select(Asset).where(Asset.symbol == "NVDA", Asset.asset_type == "stock"))).scalar_one()
    crypto = (await db.execute(select(Asset).where(Asset.symbol == "BTC"))).scalar_one()

    base = (datetime.now(UTC) - timedelta(days=2)).replace(minute=0, second=0, microsecond=0)
    candles = _full_candles(base, MIN_INTRADAY_OBS + 5)
    last_common_ts = candles[-1].bucket_ts
    await ingest_intraday_candles(db, stock.id, candles, provider="test", is_demo=False)
    await ingest_intraday_candles(db, crypto.id, candles, provider="test", is_demo=False)
    await db.commit()

    before_recompute = datetime.now(UTC)
    await recompute_intraday_scores_for_stock(db, stock, [crypto])

    row = (await db.execute(select(IntradayExposureScore).where(
        IntradayExposureScore.stock_id == stock.id, IntradayExposureScore.crypto_id == crypto.id,
    ))).scalar_one()
    data_ts = row.data_ts if row.data_ts.tzinfo is not None else row.data_ts.replace(tzinfo=UTC)
    assert data_ts == last_common_ts
    assert data_ts < before_recompute  # not the compute-time wall clock


@pytest.mark.asyncio
async def test_recompute_pair_is_demo_when_either_side_is_demo(db: AsyncSession) -> None:
    stock = (await db.execute(select(Asset).where(Asset.symbol == "NVDA", Asset.asset_type == "stock"))).scalar_one()
    crypto = (await db.execute(select(Asset).where(Asset.symbol == "BTC"))).scalar_one()

    base = (datetime.now(UTC) - timedelta(days=2)).replace(minute=0, second=0, microsecond=0)
    candles = _full_candles(base, MIN_INTRADAY_OBS + 5)
    await ingest_intraday_candles(db, stock.id, candles, provider="test", is_demo=False)
    await ingest_intraday_candles(db, crypto.id, candles, provider="test", is_demo=True)
    await db.commit()

    await recompute_intraday_scores_for_stock(db, stock, [crypto])

    row = (await db.execute(select(IntradayExposureScore).where(
        IntradayExposureScore.stock_id == stock.id, IntradayExposureScore.crypto_id == crypto.id,
    ))).scalar_one()
    assert row.is_demo is True


@pytest.mark.asyncio
async def test_recompute_removes_obsolete_pair_after_new_set_written(db: AsyncSession) -> None:
    stock = (await db.execute(select(Asset).where(Asset.symbol == "NVDA", Asset.asset_type == "stock"))).scalar_one()
    btc = (await db.execute(select(Asset).where(Asset.symbol == "BTC"))).scalar_one()
    eth = (await db.execute(select(Asset).where(Asset.symbol == "ETH"))).scalar_one()

    base = (datetime.now(UTC) - timedelta(days=2)).replace(minute=0, second=0, microsecond=0)
    candles = _full_candles(base, MIN_INTRADAY_OBS + 5)
    await ingest_intraday_candles(db, stock.id, candles, provider="test", is_demo=False)
    await ingest_intraday_candles(db, btc.id, candles, provider="test", is_demo=False)
    await ingest_intraday_candles(db, eth.id, candles, provider="test", is_demo=False)
    await db.commit()

    await recompute_intraday_scores_for_stock(db, stock, [btc, eth])
    rows = (await db.execute(select(IntradayExposureScore).where(IntradayExposureScore.stock_id == stock.id))).scalars().all()
    assert {r.crypto_id for r in rows} == {btc.id, eth.id}

    # ETH removed from the catalogue — the next run only considers BTC.
    await recompute_intraday_scores_for_stock(db, stock, [btc])
    rows = (await db.execute(select(IntradayExposureScore).where(IntradayExposureScore.stock_id == stock.id))).scalars().all()
    assert {r.crypto_id for r in rows} == {btc.id}


@pytest.mark.asyncio
async def test_intraday_endpoint_collecting_data_when_no_pair_aligned(client: AsyncClient, db: AsyncSession) -> None:
    """Stock has plenty of its own candles, but every crypto pair is still
    below the alignment threshold — must report collecting_data, not ready
    with an empty score list."""
    stock = (await db.execute(select(Asset).where(Asset.symbol == "NVDA", Asset.asset_type == "stock"))).scalar_one()
    crypto = (await db.execute(select(Asset).where(Asset.symbol == "BTC"))).scalar_one()

    base = (datetime.now(UTC) - timedelta(days=2)).replace(minute=0, second=0, microsecond=0)
    stock_candles = _full_candles(base, MIN_INTRADAY_OBS + 5)
    await ingest_intraday_candles(db, stock.id, stock_candles, provider="test", is_demo=True)
    await ingest_intraday_candles(db, crypto.id, stock_candles[:5], provider="test", is_demo=True)
    await db.commit()

    await recompute_intraday_scores_for_stock(db, stock, [crypto])

    r = await client.get("/api/v1/intraday/NVDA")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "collecting_data"
    assert body["scores"] == []
    assert body["current_count"] == 5


@pytest.mark.asyncio
async def test_intraday_endpoint_scores_ordered_by_abs_score_desc_then_symbol(client: AsyncClient, db: AsyncSession) -> None:
    await seed_fixture_intraday_data(db)
    r = await client.get("/api/v1/intraday/NVDA")
    scores = r.json()["scores"]
    assert len(scores) > 1
    expected = sorted(scores, key=lambda s: (-abs(s["score"]), s["symbol"]))
    assert scores == expected
