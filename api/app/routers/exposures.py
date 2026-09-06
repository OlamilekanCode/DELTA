from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.asset import Asset
from app.models.exposure_score import StoredExposureScore
from app.models.price import DailyPrice
from app.schemas.correlation import ExposureScoreOut, StockInfo
from app.schemas.exposures import ExposuresResult
from app.services.scoring import recompute_all_scores

router = APIRouter()

_STALE_HOURS = 25


@router.get("/exposures/{stock_symbol}", response_model=ExposuresResult)
async def get_exposures(
    stock_symbol: str,
    db: AsyncSession = Depends(get_db),
) -> ExposuresResult:
    symbol = stock_symbol.upper()

    stock_result = await db.execute(
        select(Asset).where(Asset.symbol == symbol, Asset.asset_type == "stock")
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol!r} not found")

    stored_result = await db.execute(
        select(StoredExposureScore)
        .where(StoredExposureScore.stock_id == stock.id)
        .order_by(StoredExposureScore.score.desc())
    )
    stored = stored_result.scalars().all()

    # Compute on-demand and cache if no stored scores exist
    if not stored:
        await recompute_all_scores(db)
        stored_result2 = await db.execute(
            select(StoredExposureScore)
            .where(StoredExposureScore.stock_id == stock.id)
            .order_by(StoredExposureScore.score.desc())
        )
        stored = stored_result2.scalars().all()

    computed_at: datetime | None = stored[0].computed_at if stored else None
    stale = False
    if computed_at:
        age = datetime.now(UTC) - computed_at.replace(tzinfo=UTC)
        stale = age > timedelta(hours=_STALE_HOURS)

    is_demo = any(s.is_demo for s in stored) if stored else True

    crypto_ids = [s.crypto_id for s in stored]
    crypto_result = await db.execute(select(Asset).where(Asset.id.in_(crypto_ids)))
    crypto_by_id = {a.id: a for a in crypto_result.scalars().all()}

    # Determine demo from actual price rows when stored scores say is_demo=True
    if is_demo:
        any_demo = await db.execute(
            select(DailyPrice.is_demo)
            .where(DailyPrice.asset_id == stock.id, DailyPrice.is_demo == True)  # noqa: E712
            .limit(1)
        )
        is_demo = any_demo.scalar() is True

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
        ))

    return ExposuresResult(
        stock=StockInfo(symbol=stock.symbol, name=stock.name),
        scores=scores,
        computed_at=computed_at,
        stale=stale,
        demo=is_demo,
    )
