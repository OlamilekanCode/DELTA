"""SIWE (ERC-4361) wallet authentication: nonce issuance, message verification,
and opaque server-side sessions. Session tokens are never stored — only their
HMAC-SHA256 digest (keyed by SESSION_SECRET) — so a database leak alone
cannot be used to impersonate a session, and cannot be replayed even if an
attacker also learns SESSION_SECRET without the original token.
"""

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from eth_account import Account
from eth_account.messages import encode_defunct
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.auth import AuthNonce, Session, WalletUser

NONCE_TTL = timedelta(minutes=5)
SESSION_TTL = timedelta(days=30)

_MAX_MESSAGE_LENGTH = 2048
_MAX_SIGNATURE_LENGTH = 300  # a standard 65-byte ECDSA sig hex-encodes to 132 chars; generous headroom
_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")

_FIELD_PATTERNS = {
    "uri": re.compile(r"^URI: (.+)$", re.MULTILINE),
    "version": re.compile(r"^Version: (.+)$", re.MULTILINE),
    "chain_id": re.compile(r"^Chain ID: (.+)$", re.MULTILINE),
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
    if len(message) > _MAX_MESSAGE_LENGTH:
        raise SiweError("message_too_long")

    lines = message.splitlines()
    if len(lines) < 2:
        raise SiweError("malformed_message")

    domain_match = _DOMAIN_LINE_RE.match(lines[0])
    if not domain_match:
        raise SiweError("malformed_message")

    address = lines[1].strip()
    if not _ADDRESS_RE.match(address):
        raise SiweError("malformed_address")

    fields = {"domain": domain_match.group(1), "address": address}
    for key, pattern in _FIELD_PATTERNS.items():
        matches = pattern.findall(message)
        if not matches:
            raise SiweError(f"missing_field_{key}")
        if len(matches) > 1:
            raise SiweError(f"duplicate_field_{key}")
        fields[key] = matches[0]

    if fields["version"] != "1":
        raise SiweError("unsupported_version")

    return fields


def _validate_uri(uri: str, allowed_uris: set[str]) -> None:
    parsed = urlparse(uri)
    if parsed.scheme not in ("http", "https"):
        raise SiweError("uri_scheme_invalid")
    if not parsed.netloc:
        raise SiweError("uri_host_invalid")
    if uri.rstrip("/") not in allowed_uris:
        raise SiweError("uri_mismatch")


async def verify_siwe_message(db: AsyncSession, message: str, signature: str) -> WalletUser:
    """Validate the complete EIP-4361 structure (domain, address, URI, version,
    chain ID, nonce, issued-at/expiry, no duplicate fields), the signature,
    then atomically consume the nonce (replay protection) and upsert the
    wallet user.

    Raises RuntimeError if the chain isn't configured yet, SiweError otherwise.
    """
    settings = get_settings()
    if settings.synthex_chain_id == 0:
        raise RuntimeError("chain not configured")

    if len(signature) > _MAX_SIGNATURE_LENGTH:
        raise SiweError("signature_too_long")

    fields = _parse_siwe_message(message)

    if fields["domain"] not in settings.parsed_siwe_domains:
        raise SiweError("domain_mismatch")
    _validate_uri(fields["uri"], settings.parsed_siwe_uris)

    try:
        chain_id = int(fields["chain_id"])
    except ValueError as e:
        raise SiweError("malformed_chain_id") from e
    if chain_id != settings.synthex_chain_id:
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

    # Verify the signature BEFORE consuming the nonce — an unauthenticated
    # caller must never be able to burn someone else's nonce.
    try:
        recovered = Account.recover_message(encode_defunct(text=message), signature=signature)
    except Exception as e:
        raise SiweError("invalid_signature") from e

    if recovered.lower() != fields["address"].lower():
        raise SiweError("signature_address_mismatch")

    # Atomic conditional consume: UPDATE ... WHERE used = false. A concurrent
    # second request for the same nonce gets rowcount == 0 and fails closed,
    # instead of a SELECT-then-UPDATE race where both could pass the check.
    nonce_result = await db.execute(select(AuthNonce).where(AuthNonce.nonce == fields["nonce"]))
    nonce_row = nonce_result.scalar_one_or_none()
    if nonce_row is None:
        raise SiweError("invalid_nonce")
    if nonce_row.expires_at.replace(tzinfo=UTC) < now:
        raise SiweError("nonce_expired")

    consume_result = await db.execute(
        update(AuthNonce)
        .where(AuthNonce.id == nonce_row.id, AuthNonce.used == False)  # noqa: E712
        .values(used=True)
    )
    if consume_result.rowcount == 0:
        raise SiweError("nonce_reused")

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


def _hash_token(token: str, settings: Settings | None = None) -> str:
    """HMAC-SHA256 of the session token, keyed by SESSION_SECRET (a pepper).

    Using HMAC instead of a bare SHA-256 digest means a stolen database dump
    alone is insufficient to forge a valid Authorization header — the
    attacker would also need SESSION_SECRET, which never leaves the server.
    """
    settings = settings or get_settings()
    key = settings.session_secret.encode()
    return hmac.new(key, token.encode(), hashlib.sha256).hexdigest()


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


async def cleanup_expired_auth_rows(db: AsyncSession) -> dict:
    """Idempotently delete expired nonces and long-expired sessions. Safe to
    run repeatedly — deleting already-deleted rows is a no-op."""
    from sqlalchemy import delete

    now = datetime.now(UTC)
    nonce_result = await db.execute(delete(AuthNonce).where(AuthNonce.expires_at < now))
    # Keep revoked/expired sessions a little past expiry for audit purposes,
    # then drop them — 30 days past expiry mirrors the session TTL itself.
    session_cutoff = now - timedelta(days=30)
    session_result = await db.execute(delete(Session).where(Session.expires_at < session_cutoff))
    await db.commit()
    return {"nonces_deleted": nonce_result.rowcount, "sessions_deleted": session_result.rowcount}
