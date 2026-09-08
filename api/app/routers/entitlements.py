from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_auth
from app.services.holder import cached_balance, is_verified_holder, refresh_wallet_balance
from app.services.portfolio import get_or_create_entitlement
from app.services.purchase_verification import verify_purchase

router = APIRouter(prefix="/entitlements")


def _format_balance(balance_raw: str, decimals: int) -> str:
    value = Decimal(balance_raw) / Decimal(10**decimals)
    return f"{value:,.2f}"


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

    # Best-effort — a stale/failed balance refresh must not undo a verified purchase.
    await refresh_wallet_balance(db, wallet)
    return result


@router.get("/status")
async def entitlements_status(
    wallet: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    entitlement = await get_or_create_entitlement(db, wallet)
    is_holder = await is_verified_holder(db, wallet)
    balance_row = await cached_balance(db, wallet)
    settings = get_settings()

    return {
        "tier": entitlement.tier,
        "cumulative_usd": entitlement.cumulative_usd_cents / 100,
        "is_holder": is_holder,
        # Null (never a false zero) whenever no cached balance exists yet —
        # e.g. the token contract is unconfigured, or refresh hasn't run.
        "synthex_balance_raw": balance_row.balance_raw if balance_row else None,
        "synthex_balance": (
            _format_balance(balance_row.balance_raw, settings.synthex_token_decimals)
            if balance_row else None
        ),
        "synthex_balance_checked_at": balance_row.checked_at.isoformat() if balance_row else None,
    }


@router.post("/refresh")
async def refresh_entitlements(
    wallet: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await refresh_wallet_balance(db, wallet)
    return result.as_dict()
