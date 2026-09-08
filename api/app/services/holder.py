"""$SynthEx holder-status checks, read from the cached_wallet_balances table.

Never reads on-chain per-request (see CLAUDE.md: provider/RPC calls only run
through scheduled or explicit refresh jobs). Fails closed whenever the chain
or token isn't configured, or no fresh cached balance exists — never assumes
holder access.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.auth import CachedWalletBalance

CACHE_TTL = timedelta(minutes=5)


async def is_verified_holder(db: AsyncSession, wallet_address: str) -> bool:
    settings = get_settings()
    if settings.synthex_chain_id == 0 or not settings.synthex_token_address:
        return False

    result = await db.execute(
        select(CachedWalletBalance).where(
            CachedWalletBalance.wallet_address == wallet_address.lower(),
            CachedWalletBalance.token_address == settings.synthex_token_address.lower(),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return False
    if row.checked_at.replace(tzinfo=UTC) < datetime.now(UTC) - CACHE_TTL:
        return False
    return row.is_holder
