"""SIWE (ERC-4361) wallet authentication: nonce issuance, message verification,
and opaque server-side sessions. Session tokens are never stored — only their
SHA-256 hash — so a database leak alone cannot be used to impersonate a session.
"""

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from eth_account import Account
from eth_account.messages import encode_defunct
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.auth import AuthNonce, Session, WalletUser

NONCE_TTL = timedelta(minutes=5)
SESSION_TTL = timedelta(days=30)

_FIELD_PATTERNS = {
    "uri": re.compile(r"^URI: (.+)$", re.MULTILINE),
    "chain_id": re.compile(r"^Chain ID: (\d+)$", re.MULTILINE),
    "nonce": re.compile(r"^Nonce: (.+)$", re.MULTILINE),
    "issued_at": re.compile(r"^Issued At: (.+)$", re.MULTILINE),
    "expiration_time": re.compile(r"^Expiration Time: (.+)$", re.MULTILINE),
}
_DOMAIN_LINE_RE = re.compile(r"^(.+) wants you to sign in with your Ethereum account:$")


class SiweError(ValueError):
    """A SIWE message or signature failed verification. `code` is machine-readable."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def generate_nonce() -> str:
    return secrets.token_hex(16)  # 128 bits


async def create_nonce(db: AsyncSession) -> tuple[str, datetime]:
    nonce = generate_nonce()
    expires_at = datetime.now(UTC) + NONCE_TTL
    db.add(AuthNonce(nonce=nonce, expires_at=expires_at, used=False, created_at=datetime.now(UTC)))
    await db.commit()
    return nonce, expires_at


def _parse_siwe_message(message: str) -> dict[str, str]:
    lines = message.splitlines()
    if len(lines) < 2:
        raise SiweError("malformed_message")

    domain_match = _DOMAIN_LINE_RE.match(lines[0])
    if not domain_match:
        raise SiweError("malformed_message")

    fields = {"domain": domain_match.group(1), "address": lines[1].strip()}
    for key, pattern in _FIELD_PATTERNS.items():
        m = pattern.search(message)
        if not m:
            raise SiweError(f"missing_field_{key}")
        fields[key] = m.group(1)
    return fields


def _allowed_domains(settings: Settings) -> set[str]:
    return {urlparse(o).netloc or o for o in settings.parsed_cors_origins}


async def verify_siwe_message(db: AsyncSession, message: str, signature: str) -> WalletUser:
    """Validate domain, URI, chain ID, nonce, issued-at/expiry and the signature,
    then consume the nonce (replay protection) and upsert the wallet user.

    Raises RuntimeError if the chain isn't configured yet, SiweError otherwise.
    """
    settings = get_settings()
    if settings.synthex_chain_id == 0:
        raise RuntimeError("chain not configured")

    fields = _parse_siwe_message(message)
    allowed = _allowed_domains(settings)

    if fields["domain"] not in allowed:
        raise SiweError("domain_mismatch")
    if urlparse(fields["uri"]).netloc not in allowed:
        raise SiweError("uri_mismatch")
    if int(fields["chain_id"]) != settings.synthex_chain_id:
        raise SiweError("chain_mismatch")

    now = datetime.now(UTC)
    try:
        issued_at = datetime.fromisoformat(fields["issued_at"].replace("Z", "+00:00"))
        expiration = datetime.fromisoformat(fields["expiration_time"].replace("Z", "+00:00"))
    except ValueError as e:
        raise SiweError("malformed_timestamp") from e
    if now > expiration:
        raise SiweError("message_expired")
    if issued_at > now + timedelta(minutes=1):
        raise SiweError("issued_in_future")

    nonce_result = await db.execute(select(AuthNonce).where(AuthNonce.nonce == fields["nonce"]))
    nonce_row = nonce_result.scalar_one_or_none()
    if nonce_row is None:
        raise SiweError("invalid_nonce")
    if nonce_row.used:
        raise SiweError("nonce_reused")
    if nonce_row.expires_at.replace(tzinfo=UTC) < now:
        raise SiweError("nonce_expired")

    try:
        recovered = Account.recover_message(encode_defunct(text=message), signature=signature)
    except Exception as e:
        raise SiweError("invalid_signature") from e

    if recovered.lower() != fields["address"].lower():
        raise SiweError("signature_address_mismatch")

    nonce_row.used = True

    wallet_address = recovered.lower()
    wallet_result = await db.execute(
        select(WalletUser).where(WalletUser.wallet_address == wallet_address)
    )
    wallet = wallet_result.scalar_one_or_none()
    if wallet is None:
        wallet = WalletUser(wallet_address=wallet_address, created_at=now, last_seen_at=now)
        db.add(wallet)
        await db.flush()
    else:
        wallet.last_seen_at = now

    await db.commit()
    return wallet


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def create_session(db: AsyncSession, wallet: WalletUser) -> tuple[str, datetime]:
    token = secrets.token_hex(32)  # 256 bits, single-use opaque session token
    expires_at = datetime.now(UTC) + SESSION_TTL
    db.add(Session(
        wallet_user_id=wallet.id,
        token_hash=_hash_token(token),
        expires_at=expires_at,
        revoked_at=None,
        created_at=datetime.now(UTC),
    ))
    await db.commit()
    return token, expires_at


async def get_session_wallet(db: AsyncSession, token: str) -> str | None:
    result = await db.execute(
        select(Session, WalletUser)
        .join(WalletUser, WalletUser.id == Session.wallet_user_id)
        .where(Session.token_hash == _hash_token(token))
    )
    row = result.first()
    if row is None:
        return None
    session, wallet = row
    now = datetime.now(UTC)
    if session.revoked_at is not None:
        return None
    if session.expires_at.replace(tzinfo=UTC) < now:
        return None
    return wallet.wallet_address


async def revoke_session(db: AsyncSession, token: str) -> None:
    result = await db.execute(select(Session).where(Session.token_hash == _hash_token(token)))
    session = result.scalar_one_or_none()
    if session is not None:
        session.revoked_at = datetime.now(UTC)
        await db.commit()
