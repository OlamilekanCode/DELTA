from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.asset import Asset
from app.models.price import DailyPrice
from app.schemas.correlation import (
    CorrelationResult,
    ExposureScoreOut,
    PriceSeriesOut,
    PriceSeriesPoint,
    StockInfo,
)
from app.services.correlation import PricePoint, compute_exposure_scores, normalize_base100

router = APIRouter()

_CHART_SYMBOLS = {"BTC", "ETH", "SOL"}


async def _load_prices(db: AsyncSession, asset_id: int, days: int) -> list[PricePoint]:
    result = await db.execute(
        select(DailyPrice.date, DailyPrice.close)
        .where(DailyPrice.asset_id == asset_id)
        .order_by(DailyPrice.date.desc())
        .limit(days)
    )
    rows = result.all()
    # Reverse to chronological order
    return [PricePoint(date=r.date, close=r.close) for r in reversed(rows)]


@router.get("/correlation/{stock_symbol}", response_model=CorrelationResult)
async def get_correlation(
    stock_symbol: str,
    days: int = 90,
    db: AsyncSession = Depends(get_db),
) -> CorrelationResult:
    symbol = stock_symbol.upper()

    stock_result = await db.execute(
        select(Asset).where(Asset.symbol == symbol, Asset.asset_type == "stock")
    )
    stock_asset = stock_result.scalar_one_or_none()
    if not stock_asset:
        raise HTTPException(status_code=404, detail=f"Stock {symbol!r} not found")

    crypto_result = await db.execute(
        select(Asset).where(Asset.asset_type == "crypto").order_by(Asset.symbol)
    )
    crypto_assets = crypto_result.scalars().all()

    stock_prices = await _load_prices(db, stock_asset.id, days)
    if len(stock_prices) < 2:
        raise HTTPException(status_code=422, detail="Insufficient price data for this asset")

    crypto_map: dict[str, tuple[str, str, list[PricePoint]]] = {}
    for asset in crypto_assets:
        prices = await _load_prices(db, asset.id, days)
        if len(prices) >= 2:
            crypto_map[asset.symbol] = (asset.name, asset.category, prices)

    scores = compute_exposure_scores(stock_prices, crypto_map)

    stock_norm = normalize_base100([p.close for p in stock_prices])
    stock_series = [
        PriceSeriesPoint(date=stock_prices[i].date, value=v) for i, v in enumerate(stock_norm)
    ]

    crypto_series: dict[str, list[PriceSeriesPoint]] = {}
    for sym in _CHART_SYMBOLS:
        if sym in crypto_map:
            _, _, prices = crypto_map[sym]
            norm = normalize_base100([p.close for p in prices])
            crypto_series[sym] = [
                PriceSeriesPoint(date=prices[i].date, value=v) for i, v in enumerate(norm)
            ]

    settings = get_settings()
    return CorrelationResult(
        stock=StockInfo(symbol=stock_asset.symbol, name=stock_asset.name),
        scores=[
            ExposureScoreOut(
                symbol=s.symbol,
                name=s.name,
                category=s.category,
                score=s.score,
                raw_correlation=s.raw_correlation,
                observations=s.observations,
            )
            for s in scores
        ],
        price_series=PriceSeriesOut(stock=stock_series, crypto=crypto_series),
        demo=settings.use_demo_data,
        generated_at=datetime.now(UTC),
    )
