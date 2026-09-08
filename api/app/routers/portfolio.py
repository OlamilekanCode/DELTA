from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_auth
from app.services.holder import is_verified_holder
from app.services.portfolio import (
    compute_portfolio_exposure,
    get_or_create_entitlement,
    refresh_wallet_positions,
)

router = APIRouter(prefix="/portfolio")


@router.post("/refresh")
async def refresh_portfolio(
    wallet: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Explicit refresh of on-chain wallet positions. Safe to call with no
    configured RPC/contracts — it simply refreshes nothing (see
    services/portfolio_assets.py) rather than erroring."""
    positions = await refresh_wallet_positions(db, wallet)
    return {"positions_refreshed": len(positions)}


@router.get("/exposure")
async def get_portfolio_exposure(
    stock: str | None = Query(default=None, max_length=20),
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

    # Verified purchase tier is persistent, but active access still requires
    # the wallet's CURRENT $SynthEx balance to clear the holder threshold —
    # dropping below it suspends access without discarding the recorded tier.
    if not await is_verified_holder(db, wallet):
        return {
            "tier": entitlement.tier,
            "cumulative_usd": cumulative_usd,
            "status": "suspended",
            "message": "Portfolio access is suspended — your current $SynthEx balance is below the holder threshold",
        }

    exposure = await compute_portfolio_exposure(db, wallet, stock_symbol=stock)
    return {
        "tier": entitlement.tier,
        "cumulative_usd": cumulative_usd,
        "status": "active",
        "demo": get_settings().use_demo_data,
        **exposure,
    }
