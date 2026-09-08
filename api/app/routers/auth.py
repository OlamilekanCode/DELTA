from fastapi import APIRouter, Depends, HTTPException
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

router = APIRouter(prefix="/auth")


class NonceOut(BaseModel):
    nonce: str
    expires_at: str


@router.post("/nonce", response_model=NonceOut)
async def issue_nonce(db: AsyncSession = Depends(get_db)) -> NonceOut:
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
async def verify(body: VerifyIn, db: AsyncSession = Depends(get_db)) -> VerifyOut:
    try:
        wallet = await verify_siwe_message(db, body.message, body.signature)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="chain_not_configured")
    except SiweError as e:
        raise HTTPException(status_code=401, detail=e.code)

    token, expires_at = await create_session(db, wallet)
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
