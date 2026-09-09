from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.runner import seed_fixture_intraday_data
from app.models.asset import Asset
from app.models.intraday_price import IntradayPrice


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


async def _seed_crypto_candles(db: AsyncSession, symbol: str, bucket_offsets_hours: list[float]) -> None:
    """Insert IntradayPrice rows directly at controlled offsets from now, bypassing
    the fixture provider's stock-session-shaped generator — crypto trades
    continuously, so its range semantics must be tested against a real
    time-cutoff spread rather than session-bounded fixture data."""
    result = await db.execute(select(Asset).where(Asset.symbol == symbol))
    asset = result.scalar_one()
    now = datetime.now(UTC)
    for hours_ago in bucket_offsets_hours:
        bucket_ts = now - timedelta(hours=hours_ago)
        db.add(
            IntradayPrice(
                asset_id=asset.id,
                bucket_ts=bucket_ts,
                interval="30m",
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                provider="fixture",
                sample_count=3,
                is_demo=True,
                created_at=now,
                updated_at=now,
            )
        )
    await db.commit()


@pytest.mark.asyncio
async def test_history_crypto_range_uses_continuous_time_cutoff(
    client: AsyncClient, db: AsyncSession
) -> None:
    # Spread candles across 40 days so each range boundary (4h/24h/7d/30d) has
    # points on both sides of the cutoff.
    offsets = [1, 3, 5, 12, 23, 25, 48, 100, 200, 400, 700, 900]
    await _seed_crypto_candles(db, "BTC", offsets)

    r_4h = await client.get("/api/v1/assets/BTC/history?range=4H")
    assert r_4h.status_code == 200
    body_4h = r_4h.json()
    assert len(body_4h["prices"]) == len([h for h in offsets if h <= 4])

    r_1d = await client.get("/api/v1/assets/BTC/history?range=1D")
    body_1d = r_1d.json()
    assert len(body_1d["prices"]) == len([h for h in offsets if h <= 24])

    r_1w = await client.get("/api/v1/assets/BTC/history?range=1W")
    body_1w = r_1w.json()
    assert len(body_1w["prices"]) == len([h for h in offsets if h <= 24 * 7])

    r_1m = await client.get("/api/v1/assets/BTC/history?range=1M")
    body_1m = r_1m.json()
    assert len(body_1m["prices"]) == len([h for h in offsets if h <= 24 * 30])
    # Never gated by the stock 13/65/260 bucket counts, and never a naive
    # hours*2 that always overcounts by one still-open bucket — expected is
    # the count of buckets that could actually have closed by now, which is
    # usually 2*720-1=1439 and only 1440 in the rare exact-boundary instant.
    assert body_1m["expected_point_count"] in (24 * 30 * 2 - 1, 24 * 30 * 2)


@pytest.mark.asyncio
async def test_history_intraday_completeness_metadata_after_seeding(
    client: AsyncClient, db: AsyncSession
) -> None:
    await seed_fixture_intraday_data(db)
    r = await client.get("/api/v1/assets/NVDA/history?range=1D")
    body = r.json()
    assert body["requested_range"] == "1D"
    assert body["point_count"] == 13
    assert body["expected_point_count"] == 13
    assert body["completeness"] == 1.0
    assert body["range_start"] is not None
    assert body["range_end"] is not None


@pytest.mark.asyncio
async def test_history_daily_completeness_metadata_present(client: AsyncClient) -> None:
    r = await client.get("/api/v1/assets/NVDA/history?range=3M")
    body = r.json()
    assert body["requested_range"] == "3M"
    assert body["point_count"] == len(body["prices"])
    assert body["expected_point_count"] is not None
    assert body["completeness"] is not None
    assert 0.0 <= body["completeness"] <= 1.0


@pytest.mark.asyncio
async def test_history_stock_1w_spans_five_sessions_not_flat_limit(
    client: AsyncClient, db: AsyncSession
) -> None:
    from app.services.market_calendar import recent_session_dates, session_open_close

    await seed_fixture_intraday_data(db)
    r = await client.get("/api/v1/assets/NVDA/history?range=1W")
    body = r.json()

    # Sum actual per-session bucket counts rather than assuming a flat 13 —
    # an NYSE early-close session in the window has fewer, and a hardcoded
    # 5*13 would spuriously fail on those days even though the response is
    # correct.
    def _session_buckets(d):
        o, c = session_open_close(d)
        return int((c - o).total_seconds() // 1800)

    expected = sum(_session_buckets(d) for d in recent_session_dates(count=5))
    assert body["expected_point_count"] == expected
    assert len(body["prices"]) == expected
    assert body["collecting_data"] is False
