"""$SynthEx holder-status checks and balance refresh.

`is_verified_holder` reads the cached_wallet_balances table only — never
reads on-chain per-request; provider/RPC calls only run through
`refresh_wallet_balance`, called from explicit/scheduled refresh points
(login, explicit refresh, after purchase verification, or a bounded
interval). Fails closed whenever the chain or token isn't configured, or no
fresh cached balance exists — never assumes holder access.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.auth import CachedWalletBalance
from app.services.blockchain import JsonRpcProvider, RpcError, RpcProvider

log = logging.getLogger(__name__)

CACHE_TTL = timedelta(minutes=5)
REFRESH_MIN_INTERVAL = timedelta(minutes=5)


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


class BalanceRefreshResult:
    def __init__(self, status: str, balance_raw: str | None = None, is_holder: bool | None = None,
                 block_number: int | None = None, message: str | None = None) -> None:
        self.status = status  # "ok" | "not_configured" | "rpc_error" | "chain_mismatch"
        self.balance_raw = balance_raw
        self.is_holder = is_holder
        self.block_number = block_number
        self.message = message

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "balance_raw": self.balance_raw,
            "is_holder": self.is_holder,
            "block_number": self.block_number,
            "message": self.message,
        }


async def refresh_wallet_balance(
    db: AsyncSession, wallet_address: str, rpc: RpcProvider | None = None
) -> BalanceRefreshResult:
    """Read the current $SynthEx ERC-20 balance for a wallet over RPC and
    upsert `cached_wallet_balances`. Fails closed (returns "not_configured")
    until SYNTHEX_CHAIN_ID, SYNTHEX_TOKEN_ADDRESS and ROBINHOOD_RPC_URL are
    all supplied. Never called on ordinary asset-page requests — only from
    explicit refresh points (see services/portfolio.py callers)."""
    settings = get_settings()
    if (
        settings.synthex_chain_id == 0
        or not settings.synthex_token_address
        or not settings.robinhood_rpc_url
    ):
        return BalanceRefreshResult(status="not_configured", message="Robinhood Chain is not configured yet")

    if not settings.synthex_holder_min_balance_raw:
        return BalanceRefreshResult(status="not_configured", message="Holder minimum balance is not configured yet")

    wallet_lower = wallet_address.lower()
    token_lower = settings.synthex_token_address.lower()

    existing_result = await db.execute(
        select(CachedWalletBalance).where(
            CachedWalletBalance.wallet_address == wallet_lower,
            CachedWalletBalance.token_address == token_lower,
        )
    )
    existing = existing_result.scalar_one_or_none()

    now = datetime.now(UTC)
    if existing is not None:
        checked_at = (
            existing.checked_at if existing.checked_at.tzinfo is not None
            else existing.checked_at.replace(tzinfo=UTC)
        )
        if now - checked_at < REFRESH_MIN_INTERVAL:
            # An authenticated user can call /entitlements/refresh repeatedly
            # — without this, every call would hit the RPC provider again,
            # letting a client trigger unbounded RPC spend. Serve the still-
            # fresh cached result instead of making another provider call.
            return BalanceRefreshResult(
                status="ok",
                balance_raw=existing.balance_raw,
                is_holder=existing.is_holder,
                block_number=existing.checked_block_number,
                message="Using cached balance — refreshed within the last 5 minutes",
            )

    provider = rpc or JsonRpcProvider(settings.robinhood_rpc_url)

    try:
        chain_id = await provider.get_chain_id()
        if chain_id != settings.synthex_chain_id:
            return BalanceRefreshResult(
                status="chain_mismatch",
                message=f"RPC reports chain {chain_id}, expected {settings.synthex_chain_id}",
            )
        balance_raw_int = await provider.get_erc20_balance(token_lower, wallet_lower)
        block_number = await provider.get_block_number()
    except RpcError:
        log.exception("RPC error refreshing wallet balance")
        return BalanceRefreshResult(status="rpc_error", message="RPC error — try again shortly")
    except Exception:  # noqa: BLE001 — any unexpected RPC/transport failure fails closed, never crashes the request
        # Never echo the raw exception — transport errors often embed the
        # request URL verbatim, and ROBINHOOD_RPC_URL may carry an API key.
        log.exception("Unexpected RPC failure refreshing wallet balance")
        return BalanceRefreshResult(status="rpc_error", message="Unexpected RPC failure")

    # Integer comparison only — token balances are never represented as float.
    min_balance_raw_int = int(settings.synthex_holder_min_balance_raw)
    is_holder = balance_raw_int >= min_balance_raw_int

    if existing is not None:
        existing.balance_raw = str(balance_raw_int)
        existing.checked_at = now
        existing.checked_block_number = block_number
        existing.is_holder = is_holder
    else:
        db.add(CachedWalletBalance(
            wallet_address=wallet_lower,
            token_address=token_lower,
            balance_raw=str(balance_raw_int),
            checked_at=now,
            checked_block_number=block_number,
            is_holder=is_holder,
        ))
    await db.commit()

    return BalanceRefreshResult(
        status="ok", balance_raw=str(balance_raw_int), is_holder=is_holder, block_number=block_number,
    )


async def cached_balance(db: AsyncSession, wallet_address: str) -> CachedWalletBalance | None:
    """Read-only lookup of the most recent cached balance row, regardless of
    freshness — used to display "12,450 SynthEx" without forcing a refresh."""
    settings = get_settings()
    if not settings.synthex_token_address:
        return None
    result = await db.execute(
        select(CachedWalletBalance).where(
            CachedWalletBalance.wallet_address == wallet_address.lower(),
            CachedWalletBalance.token_address == settings.synthex_token_address.lower(),
        )
    )
    return result.scalar_one_or_none()
