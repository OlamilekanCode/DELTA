"""30-minute intraday candle building and intraday Exposure Score calculation.

Candle return is log(close/open) per bucket — never close-to-close across
buckets — so there is no overnight or weekend return leakage.
"""

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.intraday_exposure_score import IntradayExposureScore
from app.models.intraday_price import IntradayPrice
from app.services.correlation import pearson_r

INTERVAL = "30m"
BUCKET_MINUTES = 30
MAX_SESSIONS = 20
MIN_INTRADAY_OBS = 65
MIN_SAMPLE_COUNT = 3
MODEL_VERSION = "pearson_intraday_v1"


@dataclass
class IntradayObservation:
    ts: datetime  # tz-aware UTC timestamp of a single price sample
    price: float


@dataclass
class IntradayCandle:
    bucket_ts: datetime
    open: float
    high: float
    low: float
    close: float
    sample_count: int
    data_quality: str  # "ok" | "reduced"


def _floor_bucket(ts: datetime) -> datetime:
    floored_minute = (ts.minute // BUCKET_MINUTES) * BUCKET_MINUTES
    return ts.replace(minute=floored_minute, second=0, microsecond=0)


def build_30min_candles(
    observations: list[IntradayObservation], min_sample_count: int = MIN_SAMPLE_COUNT
) -> list[IntradayCandle]:
    """Group timestamped price samples into completed 30-minute OHLC buckets.

    first=open, max=high, min=low, last=close (within each bucket, ordered by
    timestamp). Buckets with fewer than `min_sample_count` samples are marked
    "reduced" data quality rather than dropped.
    """
    buckets: dict[datetime, list[IntradayObservation]] = {}
    for obs in observations:
        if obs.price <= 0:
            continue
        buckets.setdefault(_floor_bucket(obs.ts), []).append(obs)

    candles: list[IntradayCandle] = []
    for bucket_ts, samples in sorted(buckets.items()):
        samples.sort(key=lambda o: o.ts)
        prices = [s.price for s in samples]
        candles.append(IntradayCandle(
            bucket_ts=bucket_ts,
            open=prices[0],
            high=max(prices),
            low=min(prices),
            close=prices[-1],
            sample_count=len(samples),
            data_quality="ok" if len(samples) >= min_sample_count else "reduced",
        ))
    return candles


async def ingest_intraday_candles(
    db: AsyncSession,
    asset_id: int,
    candles: list[IntradayCandle],
    provider: str,
    is_demo: bool,
) -> int:
    """Upsert IntradayPrice rows on the (asset_id, interval, bucket_ts) unique constraint."""
    if not candles:
        return 0
    now = datetime.now(UTC)
    bucket_tss = [c.bucket_ts for c in candles]
    result = await db.execute(
        select(IntradayPrice).where(
            IntradayPrice.asset_id == asset_id,
            IntradayPrice.interval == INTERVAL,
            IntradayPrice.bucket_ts.in_(bucket_tss),
        )
    )
    existing = {row.bucket_ts: row for row in result.scalars().all()}
    inserted = 0
    for c in candles:
        row = existing.get(c.bucket_ts)
        if row:
            row.open = c.open
            row.high = c.high
            row.low = c.low
            row.close = c.close
            row.sample_count = c.sample_count
            row.data_quality = c.data_quality
            row.provider = provider
            row.is_demo = is_demo
            row.updated_at = now
        else:
            db.add(IntradayPrice(
                asset_id=asset_id,
                bucket_ts=c.bucket_ts,
                interval=INTERVAL,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                sample_count=c.sample_count,
                data_quality=c.data_quality,
                provider=provider,
                is_demo=is_demo,
                created_at=now,
                updated_at=now,
            ))
            inserted += 1
    return inserted


@dataclass
class IntradayScoreResult:
    symbol: str
    name: str
    category: str
    score: float
    observations: int
    collecting_data: bool


async def _load_intraday_open_close(
    db: AsyncSession, asset_id: int, allowed_dates: set | None = None
) -> dict[datetime, tuple[float, float]]:
    cutoff = datetime.now(UTC) - timedelta(days=MAX_SESSIONS * 3)  # generous buffer for weekends
    result = await db.execute(
        select(IntradayPrice.bucket_ts, IntradayPrice.open, IntradayPrice.close)
        .where(
            IntradayPrice.asset_id == asset_id,
            IntradayPrice.interval == INTERVAL,
            IntradayPrice.bucket_ts >= cutoff,
        )
        .order_by(IntradayPrice.bucket_ts.asc())
    )
    rows = result.all()
    if allowed_dates is not None:
        rows = [r for r in rows if r.bucket_ts.date() in allowed_dates]
    return {r.bucket_ts: (r.open, r.close) for r in rows if r.open > 0 and r.close > 0}


async def compute_intraday_scores(
    db: AsyncSession,
    stock: Asset,
    crypto_assets: list[Asset],
    crypto_data_cache: dict[int, dict] | None = None,
) -> tuple[list[IntradayScoreResult], int]:
    """Pure computation (no writes). Returns (results, stock_candle_count).

    `crypto_data_cache` (asset_id -> {bucket_ts: (open, close)}, unfiltered by date)
    lets a caller iterating many stocks preload every crypto's data once instead
    of re-querying it per stock — see seed_fixture_intraday_data.
    """
    stock_data = await _load_intraday_open_close(db, stock.id)
    stock_candle_count = len(stock_data)

    if not stock_data:
        return [], 0

    # Window to the most recent MAX_SESSIONS distinct trading dates the stock has data for.
    allowed_dates = set(sorted({ts.date() for ts in stock_data}, reverse=True)[:MAX_SESSIONS])
    stock_data = {ts: v for ts, v in stock_data.items() if ts.date() in allowed_dates}

    results: list[IntradayScoreResult] = []
    for ca in crypto_assets:
        if crypto_data_cache is not None:
            raw = crypto_data_cache.get(ca.id, {})
            crypto_data = {ts: v for ts, v in raw.items() if ts.date() in allowed_dates}
        else:
            crypto_data = await _load_intraday_open_close(db, ca.id, allowed_dates=allowed_dates)
        common = sorted(set(stock_data) & set(crypto_data))
        s_rets = [math.log(stock_data[t][1] / stock_data[t][0]) for t in common]
        c_rets = [math.log(crypto_data[t][1] / crypto_data[t][0]) for t in common]
        n = len(common)
        if n < MIN_INTRADAY_OBS:
            results.append(IntradayScoreResult(
                symbol=ca.symbol, name=ca.name, category=ca.category,
                score=0.0, observations=n, collecting_data=True,
            ))
            continue
        r, n2 = pearson_r(s_rets, c_rets, min_observations=MIN_INTRADAY_OBS)
        results.append(IntradayScoreResult(
            symbol=ca.symbol, name=ca.name, category=ca.category,
            score=round(r, 4), observations=n2, collecting_data=False,
        ))

    results.sort(key=lambda x: abs(x.score), reverse=True)
    return results, stock_candle_count


async def recompute_intraday_scores_for_stock(
    db: AsyncSession,
    stock: Asset,
    crypto_assets: list[Asset],
    crypto_data_cache: dict[int, dict] | None = None,
) -> tuple[list[IntradayScoreResult], int]:
    """Compute the full result set first, then bulk-upsert atomically.

    Partial failure (an exception before commit) leaves the last stored scores
    untouched, since nothing is deleted until the full set is ready in memory.
    """
    results, stock_candle_count = await compute_intraday_scores(
        db, stock, crypto_assets, crypto_data_cache=crypto_data_cache
    )
    ready = [r for r in results if not r.collecting_data]

    if ready:
        now = datetime.now(UTC)
        demo_result = await db.execute(
            select(IntradayPrice.is_demo).where(IntradayPrice.asset_id == stock.id).limit(1)
        )
        stock_is_demo = demo_result.scalar_one_or_none()
        stock_is_demo = True if stock_is_demo is None else stock_is_demo

        crypto_by_symbol = {c.symbol: c for c in crypto_assets}
        await db.execute(delete(IntradayExposureScore).where(IntradayExposureScore.stock_id == stock.id))
        for r in ready:
            ca = crypto_by_symbol[r.symbol]
            db.add(IntradayExposureScore(
                stock_id=stock.id,
                crypto_id=ca.id,
                score=r.score,
                observations=r.observations,
                interval=INTERVAL,
                window_sessions=MAX_SESSIONS,
                data_ts=now,
                computed_at=now,
                model_version=MODEL_VERSION,
                is_demo=stock_is_demo,
                data_quality="ok",
            ))
        await db.commit()

    return results, stock_candle_count
