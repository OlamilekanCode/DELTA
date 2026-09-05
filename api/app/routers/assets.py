from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.asset import Asset
from app.schemas.asset import AssetListOut, AssetOut

router = APIRouter()


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
    return AssetListOut(assets=[AssetOut.model_validate(a) for a in assets])
