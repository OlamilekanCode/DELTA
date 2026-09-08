"""Portfolio tier derivation and (currently mocked) portfolio exposure calculation.

Tier boundaries are exact and inclusive: $49.99 -> locked, $50.00 -> summary,
$250.00 -> detailed, $1,000.00 -> premium.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import WalletEntitlement

TIER_THRESHOLDS = {
    "summary": 5_000,    # $50.00
    "detailed": 25_000,  # $250.00
    "premium": 100_000,  # $1,000.00
}


def get_tier(cumulative_usd_cents: int) -> str:
    if cumulative_usd_cents >= TIER_THRESHOLDS["premium"]:
        return "premium"
    if cumulative_usd_cents >= TIER_THRESHOLDS["detailed"]:
        return "detailed"
    if cumulative_usd_cents >= TIER_THRESHOLDS["summary"]:
        return "summary"
    return "locked"


async def get_entitlement(db: AsyncSession, wallet_address: str) -> WalletEntitlement | None:
    result = await db.execute(
        select(WalletEntitlement).where(WalletEntitlement.wallet_address == wallet_address.lower())
    )
    return result.scalar_one_or_none()


async def get_or_create_entitlement(db: AsyncSession, wallet_address: str) -> WalletEntitlement:
    entitlement = await get_entitlement(db, wallet_address)
    if entitlement is None:
        entitlement = WalletEntitlement(
            wallet_address=wallet_address.lower(),
            tier="locked",
            cumulative_usd_cents=0,
            updated_at=datetime.now(UTC),
        )
        db.add(entitlement)
        await db.commit()
    return entitlement


async def compute_portfolio_exposure(db: AsyncSession, wallet_address: str) -> dict:
    """Σ(asset portfolio weight × signed asset Exposure Score).

    Mocked pending a real wallet-positions endpoint (there is no on-chain
    multi-asset position reader yet) — returns an honest empty structure
    rather than a fabricated score, per the "never show false success" rule.
    """
    return {
        "portfolio_exposure_score": None,
        "assets": [],
        "note": "Portfolio position tracking is not yet available",
    }
