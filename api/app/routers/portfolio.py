from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_auth
from app.services.portfolio import compute_portfolio_exposure, get_or_create_entitlement

router = APIRouter(prefix="/portfolio")


@router.get("/exposure")
async def get_portfolio_exposure(
    wallet: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    entitlement = await get_or_create_entitlement(db, wallet)
    cumulative_usd = entitlement.cumulative_usd_cents / 100

    if entitlement.tier == "locked":
        return {
            "tier": "locked",
            "cumulative_usd": cumulative_usd,
            "message": "Purchase $SynthEx to unlock",
        }

    exposure = await compute_portfolio_exposure(db, wallet)
    return {
        "tier": entitlement.tier,
        "cumulative_usd": cumulative_usd,
        "portfolio_exposure_score": exposure["portfolio_exposure_score"],
        "assets": exposure["assets"],
        "note": exposure["note"],
        "demo": get_settings().use_demo_data,
    }
