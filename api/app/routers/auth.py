from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_bearer_token, get_current_wallet
from app.services.auth import (
    SiweError,
    create_nonce,
    create_session,
    revoke_session,
    verify_siwe_message,
)
from app.services.holder import refresh_wallet_balance
from app.services.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/auth")

_NONCE_RATE_LIMIT = 20  # per IP per minute
_VERIFY_RATE_LIMIT = 10  # per IP per minute


class NonceOut(BaseModel):
    nonce: str
    expires_at: str


@router.post("/nonce", response_model=NonceOut)
async def issue_nonce(request: Request, db: AsyncSession = Depends(get_db)) -> NonceOut:
    enforce_rate_limit(request, "nonce", _NONCE_RATE_LIMIT)
    nonce, expires_at = await create_nonce(db)
    return NonceOut(nonce=nonce, expires_at=expires_at.isoformat())


class VerifyIn(BaseModel):
    message: str
    signature: str


class VerifyOut(BaseModel):
    wallet_address: str
    session_token: str
    session_expires_at: str


@router.post("/verify", response_model=VerifyOut)
async def verify(body: VerifyIn, request: Request, db: AsyncSession = Depends(get_db)) -> VerifyOut:
    enforce_rate_limit(request, "verify", _VERIFY_RATE_LIMIT)
    try:
        wallet = await verify_siwe_message(db, body.message, body.signature)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="chain_not_configured")
    except SiweError as e:
        raise HTTPException(status_code=401, detail=e.code)

    token, expires_at = await create_session(db, wallet)
    # Best-effort — an RPC/config failure here must never block a successful
    # sign-in; refresh_wallet_balance already fails closed on its own.
    await refresh_wallet_balance(db, wallet.wallet_address)
    return VerifyOut(
        wallet_address=wallet.wallet_address,
        session_token=token,
        session_expires_at=expires_at.isoformat(),
    )


class SessionOut(BaseModel):
    wallet_address: str | None
    authenticated: bool


@router.get("/session", response_model=SessionOut)
async def get_session(wallet: str | None = Depends(get_current_wallet)) -> SessionOut:
    return SessionOut(wallet_address=wallet, authenticated=wallet is not None)


@router.post("/logout")
async def logout(
    token: str | None = Depends(get_bearer_token), db: AsyncSession = Depends(get_db)
) -> dict:
    if token:
        await revoke_session(db, token)
    return {"ok": True}
