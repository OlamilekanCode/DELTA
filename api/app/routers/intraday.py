import math

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import enforce_asset_access
from app.models.asset import Asset
from app.models.intraday_price import IntradayPrice
from app.schemas.correlation import StockInfo
from app.schemas.intraday import IntradayResult, IntradayScoreOut
from app.services.intraday import (
    BUCKET_MINUTES,
    MAX_SESSIONS,
    MIN_INTRADAY_OBS,
    compute_intraday_scores,
)
from app.services.market_calendar import upcoming_session_dates

router = APIRouter()

_BUCKETS_PER_SESSION = int((6.5 * 60) // BUCKET_MINUTES)  # regular NYSE session length


@router.get("/intraday/{symbol}", response_model=IntradayResult)
async def get_intraday(
    symbol: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> IntradayResult:
    stock_symbol = symbol.upper()

    stock_result = await db.execute(
        select(Asset).where(Asset.symbol == stock_symbol, Asset.asset_type == "stock")
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {stock_symbol!r} not found")
    await enforce_asset_access(request, db, stock.access)

    crypto_result = await db.execute(
        select(Asset).where(Asset.asset_type == "crypto").order_by(Asset.symbol)
    )
    crypto_assets = crypto_result.scalars().all()

    results, stock_candle_count = await compute_intraday_scores(db, stock, crypto_assets)

    demo_result = await db.execute(
        select(IntradayPrice.is_demo).where(IntradayPrice.asset_id == stock.id).limit(1)
    )
    is_demo = demo_result.scalar_one_or_none()
    is_demo = True if is_demo is None else is_demo

    if stock_candle_count < MIN_INTRADAY_OBS:
        remaining = MIN_INTRADAY_OBS - stock_candle_count
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
            current_count=stock_candle_count,
            required_count=MIN_INTRADAY_OBS,
            estimated_ready=estimated_ready,
        )

    return IntradayResult(
        stock=StockInfo(symbol=stock.symbol, name=stock.name),
        status="ready",
        scores=[
            IntradayScoreOut(
                symbol=r.symbol, name=r.name, category=r.category,
                score=r.score, observations=r.observations,
            )
            for r in results if not r.collecting_data
        ],
        interval="30m",
        sessions_used=MAX_SESSIONS,
        demo=is_demo,
    )
