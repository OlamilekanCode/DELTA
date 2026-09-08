from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.asset import Asset
from app.models.exposure_score import StoredExposureScore
from app.schemas.correlation import ExposureScoreOut, StockInfo
from app.schemas.exposures import ExposuresResult
from app.services.access import free_only_clause, require_asset_access
from app.services.freshness import historical_is_stale

router = APIRouter()


@router.get("/exposures/{stock_symbol}", response_model=ExposuresResult)
async def get_exposures(
    stock_symbol: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ExposuresResult:
    symbol = stock_symbol.upper()

    stock_result = await db.execute(
        select(Asset).where(Asset.symbol == symbol, Asset.asset_type == "stock")
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol!r} not found")
    ctx = await require_asset_access(request, db, stock)

    stored_result = await db.execute(
        select(StoredExposureScore)
        .where(StoredExposureScore.stock_id == stock.id)
        .order_by(func.abs(StoredExposureScore.score).desc())
    )
    stored = stored_result.scalars().all()

    computed_at: datetime | None = stored[0].computed_at if stored else None
    stale = historical_is_stale(computed_at)

    # is_demo is stored per-pair in stored_exposure_scores.
    # A result set is demo when any individual pair used fixture data.
    is_demo = any(s.is_demo for s in stored) if stored else True

    crypto_ids = [s.crypto_id for s in stored]
    crypto_stmt = select(Asset).where(Asset.id.in_(crypto_ids))
    clause = free_only_clause(ctx)
    if clause is not None:
        crypto_stmt = crypto_stmt.where(clause)
    crypto_result = await db.execute(crypto_stmt)
    crypto_by_id = {a.id: a for a in crypto_result.scalars().all()}

    scores: list[ExposureScoreOut] = []
    for s in stored:
        ca = crypto_by_id.get(s.crypto_id)
        if not ca:
            continue
        scores.append(ExposureScoreOut(
            symbol=ca.symbol,
            name=ca.name,
            category=ca.category,
            score=s.score,
            raw_correlation=s.raw_correlation,
            observations=s.observations,
            data_quality=s.data_quality,
            data_ts=s.data_ts.isoformat() if s.data_ts else None,
        ))

    return ExposuresResult(
        stock=StockInfo(symbol=stock.symbol, name=stock.name),
        scores=scores,
        computed_at=computed_at,
        stale=stale,
        demo=is_demo,
    )
