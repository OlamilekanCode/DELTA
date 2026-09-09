"""Deprecated compatibility alias for /exposures.

This endpoint used to compute Pearson correlation on every GET request. It
now reads the same precomputed `stored_exposure_scores` rows /exposures
serves — no Exposure Score is ever calculated inside a request handler
(ingestion and computation are separate scheduled phases from query). The stock and
crypto normalized price series are still read live from stored daily
prices for charting only; that's a display transform, not a recomputation
of the score.
"""

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.asset import Asset
from app.models.exposure_score import StoredExposureScore
from app.models.price import DailyPrice
from app.schemas.correlation import (
    CorrelationResult,
    ExposureScoreOut,
    PriceSeriesOut,
    PriceSeriesPoint,
    StockInfo,
)
from app.services.access import free_only_clause, require_asset_access
from app.services.correlation import normalize_base100

router = APIRouter()

_CHART_SYMBOLS = {"BTC", "ETH", "SOL"}


async def _load_closes(db: AsyncSession, asset_id: int, days: int) -> list[tuple[str, float]]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    result = await db.execute(
        select(DailyPrice.date, DailyPrice.close)
        .where(DailyPrice.asset_id == asset_id, DailyPrice.date >= cutoff)
        .order_by(DailyPrice.date.asc())
    )
    return [(r.date, r.close) for r in result.all()]


@router.get("/correlation/{stock_symbol}", response_model=CorrelationResult, deprecated=True)
async def get_correlation(
    stock_symbol: str,
    request: Request,
    days: int = Query(default=90, ge=60, le=90),
    db: AsyncSession = Depends(get_db),
) -> CorrelationResult:
    symbol = stock_symbol.upper()

    stock_result = await db.execute(
        select(Asset).where(Asset.symbol == symbol, Asset.asset_type == "stock")
    )
    stock_asset = stock_result.scalar_one_or_none()
    if not stock_asset:
        raise HTTPException(status_code=404, detail=f"Stock {symbol!r} not found")
    ctx = await require_asset_access(request, db, stock_asset)

    stored_stmt = (
        select(StoredExposureScore)
        .join(Asset, Asset.id == StoredExposureScore.crypto_id)
        .where(StoredExposureScore.stock_id == stock_asset.id)
    )
    clause = free_only_clause(ctx)
    if clause is not None:
        stored_stmt = stored_stmt.where(clause)
    stored_stmt = stored_stmt.order_by(func.abs(StoredExposureScore.score).desc())
    stored_result = await db.execute(stored_stmt)
    stored = stored_result.scalars().all()

    crypto_ids = [s.crypto_id for s in stored]
    crypto_result = await db.execute(select(Asset).where(Asset.id.in_(crypto_ids)))
    crypto_by_id = {a.id: a for a in crypto_result.scalars().all()}

    scores = [
        ExposureScoreOut(
            symbol=ca.symbol,
            name=ca.name,
            category=ca.category,
            score=s.score,
            raw_correlation=s.raw_correlation,
            observations=s.observations,
            data_quality=s.data_quality,
            data_ts=s.data_ts.isoformat() if s.data_ts else None,
        )
        for s in stored
        if (ca := crypto_by_id.get(s.crypto_id)) is not None
    ]

    stock_closes = await _load_closes(db, stock_asset.id, days)
    stock_norm = normalize_base100([c for _, c in stock_closes])
    stock_series = [
        PriceSeriesPoint(date=stock_closes[i][0], value=v) for i, v in enumerate(stock_norm)
    ]

    crypto_series: dict[str, list[PriceSeriesPoint]] = {}
    for sym in _CHART_SYMBOLS:
        ca = next((a for a in crypto_by_id.values() if a.symbol == sym), None)
        if ca is None:
            continue
        closes = await _load_closes(db, ca.id, days)
        norm = normalize_base100([c for _, c in closes])
        crypto_series[sym] = [PriceSeriesPoint(date=closes[i][0], value=v) for i, v in enumerate(norm)]

    is_demo = any(s.is_demo for s in stored) if stored else True

    return CorrelationResult(
        stock=StockInfo(symbol=stock_asset.symbol, name=stock_asset.name),
        scores=scores,
        price_series=PriceSeriesOut(stock=stock_series, crypto=crypto_series),
        demo=is_demo,
        generated_at=datetime.now(UTC),
    )
