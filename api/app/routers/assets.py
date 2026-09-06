from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.asset import Asset
from app.models.price import DailyPrice
from app.models.quote import AssetQuote
from app.schemas.asset import AssetHistoryOut, AssetHistoryPoint, AssetListOut, AssetOut

router = APIRouter()


async def _latest_prices(db: AsyncSession) -> dict[int, DailyPrice]:
    """Most recent DailyPrice row per asset_id."""
    sub = (
        select(DailyPrice.asset_id, func.max(DailyPrice.date).label("max_date"))
        .group_by(DailyPrice.asset_id)
        .subquery()
    )
    result = await db.execute(
        select(DailyPrice).join(
            sub,
            (DailyPrice.asset_id == sub.c.asset_id) & (DailyPrice.date == sub.c.max_date),
        )
    )
    return {row.asset_id: row for row in result.scalars().all()}


async def _latest_quotes(db: AsyncSession) -> dict[int, AssetQuote]:
    """Latest AssetQuote row per asset_id (one row per crypto asset)."""
    result = await db.execute(select(AssetQuote))
    return {row.asset_id: row for row in result.scalars().all()}


def _asset_out(
    asset: Asset,
    price_row: DailyPrice | None,
    quote_row: AssetQuote | None = None,
) -> AssetOut:
    # Crypto: prefer AssetQuote for current price and quote metadata
    if asset.asset_type == "crypto" and quote_row is not None:
        return AssetOut(
            symbol=asset.symbol,
            name=asset.name,
            category=asset.category,
            asset_type=asset.asset_type,
            coingecko_id=asset.coingecko_id,
            last_price=quote_row.price_usd,
            last_price_date=quote_row.ts.date().isoformat() if quote_row.ts else None,
            is_demo=quote_row.is_demo,
            change_24h_pct=quote_row.change_24h_pct,
            market_cap_usd=quote_row.market_cap_usd,
            volume_24h_usd=quote_row.volume_24h_usd,
            quote_ts=quote_row.ts.isoformat() if quote_row.ts else None,
            quote_provider=quote_row.provider,
        )
    # Stocks and crypto fallback: use DailyPrice
    return AssetOut(
        symbol=asset.symbol,
        name=asset.name,
        category=asset.category,
        asset_type=asset.asset_type,
        coingecko_id=asset.coingecko_id,
        last_price=price_row.close if price_row else None,
        last_price_date=price_row.date if price_row else None,
        is_demo=price_row.is_demo if price_row else None,
    )


@router.get("/assets", response_model=AssetListOut)
async def list_assets(
    type: Literal["crypto", "stock"] | None = None,
    db: AsyncSession = Depends(get_db),
) -> AssetListOut:
    stmt = select(Asset).order_by(Asset.symbol)
    if type:
        stmt = stmt.where(Asset.asset_type == type)
    result = await db.execute(stmt)
    assets = result.scalars().all()
    price_map = await _latest_prices(db)
    quote_map = await _latest_quotes(db)
    return AssetListOut(assets=[_asset_out(a, price_map.get(a.id), quote_map.get(a.id)) for a in assets])


@router.get("/assets/search", response_model=AssetListOut)
async def search_assets(
    q: str = Query(default="", max_length=100),
    type: Literal["crypto", "stock"] | None = None,
    db: AsyncSession = Depends(get_db),
) -> AssetListOut:
    stmt = select(Asset).order_by(Asset.symbol)
    if type:
        stmt = stmt.where(Asset.asset_type == type)
    if q.strip():
        pattern = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Asset.symbol).like(pattern),
                func.lower(Asset.name).like(pattern),
                func.lower(Asset.category).like(pattern),
            )
        )
    result = await db.execute(stmt)
    assets = result.scalars().all()
    price_map = await _latest_prices(db)
    quote_map = await _latest_quotes(db)
    return AssetListOut(assets=[_asset_out(a, price_map.get(a.id), quote_map.get(a.id)) for a in assets])


@router.get("/assets/{symbol}", response_model=AssetOut)
async def get_asset(symbol: str, db: AsyncSession = Depends(get_db)) -> AssetOut:
    result = await db.execute(
        select(Asset).where(func.upper(Asset.symbol) == symbol.upper())
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {symbol!r} not found")
    price_map = await _latest_prices(db)
    quote_map = await _latest_quotes(db)
    return _asset_out(asset, price_map.get(asset.id), quote_map.get(asset.id))


@router.get("/assets/{symbol}/history", response_model=AssetHistoryOut)
async def get_asset_history(
    symbol: str,
    days: int = Query(default=90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
) -> AssetHistoryOut:
    result = await db.execute(
        select(Asset).where(func.upper(Asset.symbol) == symbol.upper())
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {symbol!r} not found")

    from datetime import date, timedelta

    cutoff = (date.today() - timedelta(days=days)).isoformat()
    prices_result = await db.execute(
        select(DailyPrice)
        .where(DailyPrice.asset_id == asset.id, DailyPrice.date >= cutoff)
        .order_by(DailyPrice.date.asc())
    )
    prices = prices_result.scalars().all()

    is_demo: bool | None = None
    if prices:
        is_demo = any(p.is_demo for p in prices)

    provider = "fixture" if is_demo else ("coingecko" if asset.asset_type == "crypto" else "marketstack")

    return AssetHistoryOut(
        symbol=asset.symbol,
        asset_type=asset.asset_type,
        prices=[AssetHistoryPoint(date=p.date, close=p.close) for p in prices],
        is_demo=is_demo,
        provider=provider,
    )
