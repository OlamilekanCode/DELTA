"""Centralized asset-access enforcement and filtering.

Two catalogue tiers exist: guests/non-holders get the free
universe (8 stocks + 30 crypto), verified $SynthEx holders get the full
universe (20 stocks + 100 crypto). This module is the single place that
decides who sees what, so every endpoint that touches asset rows enforces
the same rule the same way — never left to the frontend to hide.

Holder-only single-asset requests distinguish 401 (no session at all) from
403 (authenticated but not a verified holder), per the access-matrix
requirements. List/search/graph/exposure/intraday endpoints instead filter
which rows are ever loaded, applying the restriction in the database query
itself rather than filtering an already-fetched list.
"""

from dataclasses import dataclass

from fastapi import HTTPException, Request
from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_wallet
from app.models.asset import Asset
from app.services.holder import is_verified_holder


@dataclass(frozen=True)
class AccessContext:
    wallet: str | None
    is_holder: bool

    @property
    def authenticated(self) -> bool:
        return self.wallet is not None


async def get_access_context(request: Request, db: AsyncSession) -> AccessContext:
    wallet = await get_current_wallet(request, db)
    is_holder = await is_verified_holder(db, wallet) if wallet else False
    return AccessContext(wallet=wallet, is_holder=is_holder)


async def require_asset_access(request: Request, db: AsyncSession, asset: Asset) -> AccessContext:
    """Enforce access for a single already-loaded asset.

    Free assets always pass. Holder-only assets raise 401 when there is no
    session at all, and 403 when the session is authenticated but not a
    verified holder.
    """
    ctx = await get_access_context(request, db)
    if asset.access == "holder" and not ctx.is_holder:
        if not ctx.authenticated:
            raise HTTPException(status_code=401, detail="authentication_required")
        raise HTTPException(status_code=403, detail="holder_required")
    return ctx


def free_only_clause(ctx: AccessContext) -> ColumnElement[bool] | None:
    """A WHERE clause restricting a query to free assets, or None (no
    restriction) for a verified holder. Apply this to every query that loads
    a list of assets before rows are ever fetched or serialized."""
    if ctx.is_holder:
        return None
    return Asset.access == "free"
