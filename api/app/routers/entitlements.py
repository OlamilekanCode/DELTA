from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_auth
from app.services.holder import is_verified_holder
from app.services.portfolio import get_or_create_entitlement
from app.services.purchase_verification import verify_purchase

router = APIRouter(prefix="/entitlements")


class VerifyPurchaseIn(BaseModel):
    tx_hash: str


@router.post("/verify-purchase")
async def verify_purchase_endpoint(
    body: VerifyPurchaseIn,
    wallet: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await verify_purchase(db, wallet, body.tx_hash)
    if result["status"] != "verified":
        return result

    entitlement = await get_or_create_entitlement(db, wallet)
    return {
        "status": "verified",
        "tier": entitlement.tier,
        "cumulative_usd": entitlement.cumulative_usd_cents / 100,
    }


@router.get("/status")
async def entitlements_status(
    wallet: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    entitlement = await get_or_create_entitlement(db, wallet)
    is_holder = await is_verified_holder(db, wallet)

    return {
        "tier": entitlement.tier,
        "cumulative_usd": entitlement.cumulative_usd_cents / 100,
        "is_holder": is_holder,
        # Always null, never a false zero: no live on-chain balance read exists
        # yet (see /entitlements/refresh) regardless of contract config.
        "synthex_balance": None,
    }


@router.post("/refresh")
async def refresh_entitlements(
    wallet: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    settings = get_settings()
    if not settings.robinhood_rpc_url or not settings.synthex_token_address:
        return {
            "status": "not_configured",
            "message": "Balance refresh is not configured yet",
        }

    # Real on-chain balance refresh (read the ERC-20 balance over
    # settings.robinhood_rpc_url and upsert cached_wallet_balances) is not
    # implemented — no RPC URL or token contract exists to build or test it
    # against yet. Fails closed above until real configuration is supplied.
    return {"status": "not_configured", "message": "Balance refresh is not configured yet"}
