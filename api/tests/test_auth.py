from datetime import UTC, datetime, timedelta

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.services import auth as auth_service
from app.services.auth import (
    SiweError,
    create_nonce,
    create_session,
    get_session_wallet,
    revoke_session,
    verify_siwe_message,
)

TEST_CHAIN_ID = 8453
TEST_DOMAIN = "localhost:3000"
TEST_URI = "http://localhost:3000"


def _configured_settings(**overrides) -> Settings:
    fields = dict(
        cors_origins="http://localhost:3000",
        synthex_chain_id=TEST_CHAIN_ID,
        database_url="sqlite+aiosqlite:///./test.db",
    )
    fields.update(overrides)
    return Settings(**fields)


@pytest.fixture()
def configured(monkeypatch):
    settings = _configured_settings()
    monkeypatch.setattr(auth_service, "get_settings", lambda: settings)
    return settings


@pytest.fixture()
def unconfigured(monkeypatch):
    settings = _configured_settings(synthex_chain_id=0)
    monkeypatch.setattr(auth_service, "get_settings", lambda: settings)
    return settings


def _build_message(
    address: str,
    nonce: str,
    issued_at: datetime | None = None,
    expiration: datetime | None = None,
    chain_id: int = TEST_CHAIN_ID,
    domain: str = TEST_DOMAIN,
    uri: str = TEST_URI,
) -> str:
    now = datetime.now(UTC)
    issued_at = issued_at or now
    expiration = expiration or (now + timedelta(minutes=10))
    return (
        f"{domain} wants you to sign in with your Ethereum account:\n"
        f"{address}\n"
        "\n"
        "Sign in to Synthetic Exposure.\n"
        "\n"
        f"URI: {uri}\n"
        "Version: 1\n"
        f"Chain ID: {chain_id}\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued_at.isoformat()}\n"
        f"Expiration Time: {expiration.isoformat()}\n"
    )


def _sign(account, message: str) -> str:
    return account.sign_message(encode_defunct(text=message)).signature.hex()


@pytest.mark.asyncio
async def test_verify_siwe_message_happy_path(db: AsyncSession, configured) -> None:
    account = Account.create()
    nonce, _ = await create_nonce(db)
    message = _build_message(account.address, nonce)
    signature = _sign(account, message)

    wallet = await verify_siwe_message(db, message, signature)
    assert wallet.wallet_address == account.address.lower()


@pytest.mark.asyncio
async def test_verify_siwe_message_chain_not_configured(db: AsyncSession, unconfigured) -> None:
    account = Account.create()
    nonce, _ = await create_nonce(db)
    message = _build_message(account.address, nonce)
    signature = _sign(account, message)

    with pytest.raises(RuntimeError):
        await verify_siwe_message(db, message, signature)


@pytest.mark.asyncio
async def test_verify_siwe_message_rejects_wrong_signer(db: AsyncSession, configured) -> None:
    account = Account.create()
    other = Account.create()
    nonce, _ = await create_nonce(db)
    message = _build_message(account.address, nonce)  # claims `account`'s address
    signature = _sign(other, message)  # but signed by `other`

    with pytest.raises(SiweError) as exc_info:
        await verify_siwe_message(db, message, signature)
    assert exc_info.value.code == "signature_address_mismatch"


@pytest.mark.asyncio
async def test_verify_siwe_message_rejects_unknown_nonce(db: AsyncSession, configured) -> None:
    account = Account.create()
    message = _build_message(account.address, "never-issued-nonce")
    signature = _sign(account, message)

    with pytest.raises(SiweError) as exc_info:
        await verify_siwe_message(db, message, signature)
    assert exc_info.value.code == "invalid_nonce"


@pytest.mark.asyncio
async def test_verify_siwe_message_rejects_reused_nonce(db: AsyncSession, configured) -> None:
    account = Account.create()
    nonce, _ = await create_nonce(db)
    message = _build_message(account.address, nonce)
    signature = _sign(account, message)

    await verify_siwe_message(db, message, signature)  # first use succeeds

    nonce_row_message = _build_message(account.address, nonce)
    signature2 = _sign(account, nonce_row_message)
    with pytest.raises(SiweError) as exc_info:
        await verify_siwe_message(db, nonce_row_message, signature2)
    assert exc_info.value.code == "nonce_reused"


@pytest.mark.asyncio
async def test_verify_siwe_message_rejects_expired_nonce(db: AsyncSession, configured) -> None:
    account = Account.create()
    nonce, _ = await create_nonce(db)

    from sqlalchemy import select

    from app.models.auth import AuthNonce
    result = await db.execute(select(AuthNonce).where(AuthNonce.nonce == nonce))
    row = result.scalar_one()
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await db.commit()

    message = _build_message(account.address, nonce)
    signature = _sign(account, message)
    with pytest.raises(SiweError) as exc_info:
        await verify_siwe_message(db, message, signature)
    assert exc_info.value.code == "nonce_expired"


@pytest.mark.asyncio
async def test_verify_siwe_message_rejects_wrong_chain_id(db: AsyncSession, configured) -> None:
    account = Account.create()
    nonce, _ = await create_nonce(db)
    message = _build_message(account.address, nonce, chain_id=1)  # wrong chain
    signature = _sign(account, message)

    with pytest.raises(SiweError) as exc_info:
        await verify_siwe_message(db, message, signature)
    assert exc_info.value.code == "chain_mismatch"


@pytest.mark.asyncio
async def test_verify_siwe_message_rejects_wrong_domain(db: AsyncSession, configured) -> None:
    account = Account.create()
    nonce, _ = await create_nonce(db)
    message = _build_message(account.address, nonce, domain="evil.example.com")
    signature = _sign(account, message)

    with pytest.raises(SiweError) as exc_info:
        await verify_siwe_message(db, message, signature)
    assert exc_info.value.code == "domain_mismatch"


@pytest.mark.asyncio
async def test_verify_siwe_message_rejects_expired_message(db: AsyncSession, configured) -> None:
    account = Account.create()
    nonce, _ = await create_nonce(db)
    now = datetime.now(UTC)
    message = _build_message(
        account.address, nonce, issued_at=now - timedelta(hours=1), expiration=now - timedelta(minutes=30)
    )
    signature = _sign(account, message)

    with pytest.raises(SiweError) as exc_info:
        await verify_siwe_message(db, message, signature)
    assert exc_info.value.code == "message_expired"


@pytest.mark.asyncio
async def test_session_roundtrip(db: AsyncSession, configured) -> None:
    account = Account.create()
    nonce, _ = await create_nonce(db)
    message = _build_message(account.address, nonce)
    signature = _sign(account, message)
    wallet = await verify_siwe_message(db, message, signature)

    token, expires_at = await create_session(db, wallet)
    assert expires_at > datetime.now(UTC)

    resolved = await get_session_wallet(db, token)
    assert resolved == wallet.wallet_address

    await revoke_session(db, token)
    assert await get_session_wallet(db, token) is None


@pytest.mark.asyncio
async def test_get_session_wallet_unknown_token_returns_none(db: AsyncSession) -> None:
    assert await get_session_wallet(db, "not-a-real-token") is None


@pytest.mark.asyncio
async def test_auth_endpoints_full_flow(client: AsyncClient, db: AsyncSession, monkeypatch) -> None:
    settings = _configured_settings()
    monkeypatch.setattr(auth_service, "get_settings", lambda: settings)
    from app.services import holder as holder_service
    monkeypatch.setattr(holder_service, "get_settings", lambda: settings)

    r = await client.post("/api/v1/auth/nonce")
    assert r.status_code == 200
    nonce = r.json()["nonce"]

    account = Account.create()
    message = _build_message(account.address, nonce)
    signature = _sign(account, message)

    r = await client.post("/api/v1/auth/verify", json={"message": message, "signature": signature})
    assert r.status_code == 200
    body = r.json()
    assert body["wallet_address"] == account.address.lower()
    token = body["session_token"]

    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get("/api/v1/auth/session", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"wallet_address": account.address.lower(), "authenticated": True}

    r = await client.get("/api/v1/auth/session")
    assert r.status_code == 200
    assert r.json() == {"wallet_address": None, "authenticated": False}

    r = await client.post("/api/v1/auth/logout", headers=headers)
    assert r.status_code == 200

    r = await client.get("/api/v1/auth/session", headers=headers)
    assert r.json()["authenticated"] is False


@pytest.mark.asyncio
async def test_auth_verify_fails_closed_when_chain_unconfigured(client: AsyncClient) -> None:
    # Default test settings have synthex_chain_id=0 (never configured).
    r = await client.post("/api/v1/auth/nonce")
    nonce = r.json()["nonce"]
    account = Account.create()
    message = _build_message(account.address, nonce)
    signature = _sign(account, message)

    r = await client.post("/api/v1/auth/verify", json={"message": message, "signature": signature})
    assert r.status_code == 503
    assert r.json()["detail"] == "chain_not_configured"


@pytest.mark.asyncio
async def test_holder_asset_returns_403_without_session(client: AsyncClient) -> None:
    r = await client.get("/api/v1/assets/AMZN")
    assert r.status_code == 403
    assert r.json()["detail"] == "holder_required"


@pytest.mark.asyncio
async def test_free_asset_accessible_without_session(client: AsyncClient) -> None:
    r = await client.get("/api/v1/assets/NVDA")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_holder_asset_history_returns_403(client: AsyncClient) -> None:
    r = await client.get("/api/v1/assets/AMZN/history")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_holder_stock_exposures_returns_403(client: AsyncClient) -> None:
    r = await client.get("/api/v1/exposures/AMZN")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_holder_stock_graph_returns_403(client: AsyncClient) -> None:
    r = await client.get("/api/v1/graphs/AMZN")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_holder_stock_intraday_returns_403(client: AsyncClient) -> None:
    r = await client.get("/api/v1/intraday/AMZN")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_authenticated_non_holder_still_gets_403(client: AsyncClient, db: AsyncSession, monkeypatch) -> None:
    """A verified session without a verified $SynthEx balance still fails closed."""
    settings = _configured_settings()
    monkeypatch.setattr(auth_service, "get_settings", lambda: settings)
    from app.services import holder as holder_service
    monkeypatch.setattr(holder_service, "get_settings", lambda: settings)

    r = await client.post("/api/v1/auth/nonce")
    nonce = r.json()["nonce"]
    account = Account.create()
    message = _build_message(account.address, nonce)
    signature = _sign(account, message)
    r = await client.post("/api/v1/auth/verify", json={"message": message, "signature": signature})
    token = r.json()["session_token"]

    r = await client.get("/api/v1/assets/AMZN", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert r.json()["detail"] == "holder_required"
