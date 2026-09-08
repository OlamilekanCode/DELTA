from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth import get_session_wallet
from app.services.holder import is_verified_holder

# The Render API and Vercel frontend are cross-origin, so the backend never
# sets a browser-facing cookie itself. The BFF (Next.js route handlers) owns
# the HttpOnly cookie on its own origin and forwards the session token here
# as a Bearer token — see CLAUDE.md's BFF pattern.
_BEARER_PREFIX = "Bearer "


def get_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith(_BEARER_PREFIX):
        return None
    token = auth_header[len(_BEARER_PREFIX):].strip()
    return token or None


async def get_current_wallet(request: Request, db: AsyncSession = Depends(get_db)) -> str | None:
    token = get_bearer_token(request)
    if not token:
        return None
    return await get_session_wallet(db, token)


async def require_auth(wallet: str | None = Depends(get_current_wallet)) -> str:
    if wallet is None:
        raise HTTPException(status_code=401, detail="unauthenticated")
    return wallet


async def require_holder(
    wallet: str = Depends(require_auth), db: AsyncSession = Depends(get_db)
) -> str:
    if not await is_verified_holder(db, wallet):
        raise HTTPException(status_code=403, detail="holder_required")
    return wallet


async def enforce_asset_access(request: Request, db: AsyncSession, access: str) -> None:
    """Raise 403 holder_required unless `access` is "free" or the caller is a
    verified holder. Used inline by routers gating a specific asset/pair rather
    than the whole route, since access is per-row, not per-endpoint."""
    if access != "holder":
        return
    wallet = await get_current_wallet(request, db)
    if wallet is None or not await is_verified_holder(db, wallet):
        raise HTTPException(status_code=403, detail="holder_required")
