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


def floor_to_bucket(ts: datetime) -> datetime:
    """Normalise to UTC, then floor to the start of its 30-minute bucket.

    This is the single canonical alignment used for every provider's
    candles — CoinGecko-derived crypto candles (via `build_30min_candles`)
    and Marketstack-derived stock candles alike (see
    `providers/marketstack.py`) — so the two are guaranteed to land on
    identical bucket boundaries regardless of each provider's own timezone
    or sub-minute timestamp jitter.
    """
    ts = ts.astimezone(UTC) if ts.tzinfo is not None else ts.replace(tzinfo=UTC)
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
        buckets.setdefault(floor_to_bucket(obs.ts), []).append(obs)

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


async def stock_candle_count(db: AsyncSession, stock_id: int) -> int:
    """Number of "ok"-quality completed candles available for a stock within
    the scoring window. Used only as a rough collection-progress signal for a
    stock that has never been scored at all yet — once at least one pair has
    been scored, GET /intraday reads pair-level progress from the stored
    IntradayExposureScore rows instead (see routers/intraday.py)."""
    data = await _load_intraday_open_close(db, stock_id)
    return len(data)


@dataclass
class IntradayScoreResult:
    symbol: str
    name: str
    category: str
    score: float
    observations: int
    collecting_data: bool
    data_ts: datetime | None = None  # latest aligned stock/crypto candle timestamp actually used for this pair
    is_demo: bool | None = None  # provenance of the exact window used — None when not yet meaningful
    data_quality: str = "collecting_data"  # "ok" | "collecting_data" | "mixed_provenance"


async def _load_intraday_open_close(
    db: AsyncSession, asset_id: int, allowed_dates: set | None = None
) -> dict[datetime, tuple[float, float, bool]]:
    """Reduced-quality candles (insufficient samples to trust the bucket) are
    excluded from scoring entirely — never averaged in alongside "ok"
    candles. Each entry also carries that specific candle's is_demo flag so
    a pair's score can be attributed to the exact demo/real provenance of
    the candles actually used, not just an asset-wide guess."""
    cutoff = datetime.now(UTC) - timedelta(days=MAX_SESSIONS * 3)  # generous buffer for weekends
    result = await db.execute(
        select(IntradayPrice.bucket_ts, IntradayPrice.open, IntradayPrice.close, IntradayPrice.is_demo)
        .where(
            IntradayPrice.asset_id == asset_id,
            IntradayPrice.interval == INTERVAL,
            IntradayPrice.bucket_ts >= cutoff,
            IntradayPrice.data_quality == "ok",
        )
        .order_by(IntradayPrice.bucket_ts.asc())
    )
    rows = result.all()
    if allowed_dates is not None:
        rows = [r for r in rows if r.bucket_ts.date() in allowed_dates]
    return {r.bucket_ts: (r.open, r.close, r.is_demo) for r in rows if r.open > 0 and r.close > 0}


def _partition_by_provenance(
    common: list[datetime],
    stock_data: dict[datetime, tuple[float, float, bool]],
    crypto_data: dict[datetime, tuple[float, float, bool]],
) -> tuple[list[datetime], list[datetime]]:
    """Split the aligned timestamps into a fully-real subset (both candles
    real at that timestamp) and a fully-demo subset (both demo) — a
    timestamp where one side is real and the other demo belongs to neither
    pure subset, since a single paired observation can never be honestly
    attributed to just one provenance."""
    real = [t for t in common if not stock_data[t][2] and not crypto_data[t][2]]
    demo = [t for t in common if stock_data[t][2] and crypto_data[t][2]]
    return real, demo


async def compute_intraday_scores(
    db: AsyncSession,
    stock: Asset,
    crypto_assets: list[Asset],
    crypto_data_cache: dict[int, dict] | None = None,
) -> tuple[list[IntradayScoreResult], int]:
    """Pure computation (no writes). Returns (results, stock_candle_count).

    Every crypto asset gets a result — either a real score or a
    `collecting_data` placeholder — never silently omitted, so a caller can
    persist full collection-progress information without recomputing
    anything later (see recompute_intraday_scores_for_stock).

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

        # Never combine demo and real candles in one calculation — prefer a
        # fully real-data window over a fully demo one when both reach the
        # threshold, since real data is always the more useful signal.
        real_common, demo_common = _partition_by_provenance(common, stock_data, crypto_data)
        if len(real_common) >= MIN_INTRADAY_OBS:
            window, window_is_demo = real_common, False
        elif len(demo_common) >= MIN_INTRADAY_OBS:
            window, window_is_demo = demo_common, True
        elif len(common) >= MIN_INTRADAY_OBS:
            # Enough raw aligned observations exist, but neither a pure-real
            # nor pure-demo subset reaches the threshold on its own — an
            # unresolvable provenance mix. Skip rather than silently blend
            # demo and real candles into one correlation.
            results.append(IntradayScoreResult(
                symbol=ca.symbol, name=ca.name, category=ca.category,
                score=0.0, observations=0, collecting_data=True, data_ts=common[-1],
                is_demo=None, data_quality="mixed_provenance",
            ))
            continue
        else:
            # Genuinely not enough aligned data yet, regardless of provenance.
            window, window_is_demo = common, None

        last_ts = window[-1] if window else None
        s_rets = [math.log(stock_data[t][1] / stock_data[t][0]) for t in window]
        c_rets = [math.log(crypto_data[t][1] / crypto_data[t][0]) for t in window]
        n = len(window)
        if n < MIN_INTRADAY_OBS:
            results.append(IntradayScoreResult(
                symbol=ca.symbol, name=ca.name, category=ca.category,
                score=0.0, observations=n, collecting_data=True, data_ts=last_ts,
                is_demo=window_is_demo, data_quality="collecting_data",
            ))
            continue
        r, n2 = pearson_r(s_rets, c_rets, min_observations=MIN_INTRADAY_OBS)
        results.append(IntradayScoreResult(
            symbol=ca.symbol, name=ca.name, category=ca.category,
            score=round(r, 4), observations=n2, collecting_data=False, data_ts=last_ts,
            is_demo=window_is_demo, data_quality="ok",
        ))

    results.sort(key=lambda x: (-abs(x.score), x.symbol))
    return results, stock_candle_count


async def recompute_intraday_scores_for_stock(
    db: AsyncSession,
    stock: Asset,
    crypto_assets: list[Asset],
    crypto_data_cache: dict[int, dict] | None = None,
) -> tuple[list[IntradayScoreResult], int]:
    """Compute the full result set first (both ready and still-collecting
    pairs), then upsert every pair in one transaction and remove only pairs
    no longer present in the fresh result set (e.g. a delisted asset) —
    never deleting anything until the new complete set is written, so a
    failure partway through this function leaves the last valid stored
    scores untouched.
    """
    results, stock_candle_count = await compute_intraday_scores(
        db, stock, crypto_assets, crypto_data_cache=crypto_data_cache
    )
    if not results:
        return results, stock_candle_count

    now = datetime.now(UTC)
    crypto_by_symbol = {c.symbol: c for c in crypto_assets}

    existing_result = await db.execute(
        select(IntradayExposureScore).where(IntradayExposureScore.stock_id == stock.id)
    )
    existing_by_crypto = {row.crypto_id: row for row in existing_result.scalars().all()}

    seen_crypto_ids: set[int] = set()
    for r in results:
        ca = crypto_by_symbol[r.symbol]
        seen_crypto_ids.add(ca.id)
        # Provenance and quality come directly from the exact window used to
        # compute this pair's score (see compute_intraday_scores) — never a
        # separate, coarser per-asset guess. Fail toward "demo" when the
        # window's provenance couldn't be determined (not enough data yet).
        pair_is_demo = True if r.is_demo is None else r.is_demo
        data_ts = r.data_ts or now
        data_quality = r.data_quality

        row = existing_by_crypto.get(ca.id)
        if row is not None:
            row.score = r.score
            row.observations = r.observations
            row.window_sessions = MAX_SESSIONS
            row.data_ts = data_ts
            row.computed_at = now
            row.model_version = MODEL_VERSION
            row.is_demo = pair_is_demo
            row.data_quality = data_quality
        else:
            db.add(IntradayExposureScore(
                stock_id=stock.id,
                crypto_id=ca.id,
                score=r.score,
                observations=r.observations,
                interval=INTERVAL,
                window_sessions=MAX_SESSIONS,
                data_ts=data_ts,
                computed_at=now,
                model_version=MODEL_VERSION,
                is_demo=pair_is_demo,
                data_quality=data_quality,
            ))

    # Remove only pairs that no longer appear at all in the fresh result set
    # (e.g. a crypto asset removed from the catalogue) — done last, after the
    # complete replacement set above is already staged in this transaction.
    obsolete_ids = set(existing_by_crypto) - seen_crypto_ids
    if obsolete_ids:
        await db.execute(
            delete(IntradayExposureScore).where(
                IntradayExposureScore.stock_id == stock.id,
                IntradayExposureScore.crypto_id.in_(obsolete_ids),
            )
        )

    await db.commit()
    return results, stock_candle_count
