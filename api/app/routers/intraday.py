import math

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.asset import Asset
from app.models.intraday_exposure_score import IntradayExposureScore
from app.models.intraday_price import IntradayPrice
from app.schemas.correlation import StockInfo
from app.schemas.intraday import IntradayResult, IntradayScoreOut
from app.services.access import free_only_clause, require_asset_access
from app.services.freshness import intraday_status
from app.services.intraday import BUCKET_MINUTES, MAX_SESSIONS, MIN_INTRADAY_OBS, stock_candle_count
from app.services.market_calendar import get_market_status, upcoming_session_dates

router = APIRouter()

_BUCKETS_PER_SESSION = int((6.5 * 60) // BUCKET_MINUTES)  # regular NYSE session length


async def _never_scored_progress(db: AsyncSession, stock: Asset) -> tuple[int, bool]:
    """Fallback collection-progress signal for a stock with no stored
    IntradayExposureScore rows at all yet (e.g. newly added to the
    catalogue) — its own raw candle count and candle demo flag, since there
    is no pair-level data to read progress from."""
    candle_count = await stock_candle_count(db, stock.id)
    demo_result = await db.execute(
        select(IntradayPrice.is_demo)
        .where(IntradayPrice.asset_id == stock.id, IntradayPrice.interval == "30m")
        .order_by(IntradayPrice.bucket_ts.desc())
        .limit(1)
    )
    is_demo = demo_result.scalar_one_or_none()
    return candle_count, True if is_demo is None else is_demo


@router.get("/intraday/{symbol}", response_model=IntradayResult)
async def get_intraday(
    symbol: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> IntradayResult:
    """Reads the latest stored 30-minute Exposure Scores. Never computes a
    score inside this handler — scoring happens only in the scheduled
    refresh-intraday job (see ingestion/commands.py).

    Readiness is judged from stored pair-level rows, not the stock's own
    candle count alone: `recompute_intraday_scores_for_stock` persists one
    row per stock/crypto pair regardless of whether that pair has reached
    the minimum aligned-observation threshold, marking the not-yet-ready
    ones `data_quality="collecting_data"`. A stock can have plenty of its
    own candles while every pair is still below the alignment threshold —
    that must report `collecting_data`, not `ready` with an empty list.
    """
    stock_symbol = symbol.upper()

    stock_result = await db.execute(
        select(Asset).where(Asset.symbol == stock_symbol, Asset.asset_type == "stock")
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {stock_symbol!r} not found")
    ctx = await require_asset_access(request, db, stock)

    market_status = get_market_status()

    stored_stmt = (
        select(IntradayExposureScore)
        .join(Asset, Asset.id == IntradayExposureScore.crypto_id)
        .where(IntradayExposureScore.stock_id == stock.id)
    )
    clause = free_only_clause(ctx)
    if clause is not None:
        stored_stmt = stored_stmt.where(clause)
    stored_result = await db.execute(stored_stmt)
    stored_all = stored_result.scalars().all()

    ready_rows = [s for s in stored_all if s.data_quality != "collecting_data"]

    if not ready_rows:
        if stored_all:
            # At least one pair has been scored (all still collecting) — the
            # most aligned-observation progress any pair has reached so far
            # is the honest signal, not the stock's raw candle count.
            current_count = max(s.observations for s in stored_all)
            is_demo = any(s.is_demo for s in stored_all)
        else:
            current_count, is_demo = await _never_scored_progress(db, stock)

        remaining = max(MIN_INTRADAY_OBS - current_count, 0)
        sessions_needed = max(1, math.ceil(remaining / _BUCKETS_PER_SESSION))
        upcoming = upcoming_session_dates(count=sessions_needed)
        estimated_ready = upcoming[-1].isoformat() if upcoming else None
        return IntradayResult(
            stock=StockInfo(symbol=stock.symbol, name=stock.name),
            status="collecting_data",
            scores=[],
            interval="30m",
            sessions_used=MAX_SESSIONS,
            demo=is_demo,
            current_count=current_count,
            required_count=MIN_INTRADAY_OBS,
            estimated_ready=estimated_ready,
            freshness="collecting_data",
            market_is_open=market_status.is_open,
            next_market_open=market_status.next_open.isoformat(),
        )

    crypto_ids = [s.crypto_id for s in ready_rows]
    crypto_result = await db.execute(select(Asset).where(Asset.id.in_(crypto_ids)))
    crypto_by_id = {a.id: a for a in crypto_result.scalars().all()}

    is_demo = any(s.is_demo for s in ready_rows)
    data_ts = max((s.data_ts for s in ready_rows), default=None)
    freshness = intraday_status(data_ts)

    scores = [
        IntradayScoreOut(
            symbol=ca.symbol, name=ca.name, category=ca.category,
            score=s.score, observations=s.observations,
        )
        for s in ready_rows
        if (ca := crypto_by_id.get(s.crypto_id)) is not None
    ]
    # Deterministic regardless of storage/DB row order.
    scores.sort(key=lambda s: (-abs(s.score), s.symbol))

    return IntradayResult(
        stock=StockInfo(symbol=stock.symbol, name=stock.name),
        status="ready",
        scores=scores,
        interval="30m",
        sessions_used=MAX_SESSIONS,
        demo=is_demo,
        data_ts=data_ts.isoformat() if data_ts else None,
        freshness=freshness,
        market_is_open=market_status.is_open,
        next_market_open=market_status.next_open.isoformat(),
    )
