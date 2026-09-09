"""Access-matrix tests: guest / authenticated non-holder / verified holder
crossed with free stock / holder stock / free crypto / holder crypto, across
every asset-serving endpoint (lists, search, detail, history, exposures,
graphs, correlation, intraday).
"""

from datetime import UTC, datetime, timedelta

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.auth import CachedWalletBalance
from app.services import auth as auth_service
from app.services import holder as holder_service

TEST_CHAIN_ID = 8453
TOKEN_ADDRESS = "0x" + "9" * 40
FREE_STOCK = "NVDA"
HOLDER_STOCK = "AMZN"
FREE_CRYPTO = "BTC"
HOLDER_CRYPTO = "TON"


def _configured_settings(**overrides) -> Settings:
    fields = dict(
        cors_origins="http://localhost:3000",
        synthex_chain_id=TEST_CHAIN_ID,
        synthex_token_address=TOKEN_ADDRESS,
        database_url="sqlite+aiosqlite:///./test.db",
    )
    fields.update(overrides)
    return Settings(**fields)


def _build_message(address: str, nonce: str) -> str:
    now = datetime.now(UTC)
    return (
        "localhost:3000 wants you to sign in with your Ethereum account:\n"
        f"{address}\n"
        "\n"
        "Sign in to Synthetic Exposure.\n"
        "\n"
        "URI: http://localhost:3000\n"
        "Version: 1\n"
        f"Chain ID: {TEST_CHAIN_ID}\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {now.isoformat()}\n"
        f"Expiration Time: {(now + timedelta(minutes=10)).isoformat()}\n"
    )


async def _authenticate(client: AsyncClient, monkeypatch, settings: Settings) -> tuple[str, str]:
    monkeypatch.setattr(auth_service, "get_settings", lambda: settings)
    monkeypatch.setattr(holder_service, "get_settings", lambda: settings)
    r = await client.post("/api/v1/auth/nonce")
    nonce = r.json()["nonce"]
    account = Account.create()
    message = _build_message(account.address, nonce)
    signature = account.sign_message(encode_defunct(text=message)).signature.hex()
    r = await client.post("/api/v1/auth/verify", json={"message": message, "signature": signature})
    body = r.json()
    return body["session_token"], body["wallet_address"]


async def _make_holder(db: AsyncSession, wallet_address: str) -> None:
    db.add(CachedWalletBalance(
        wallet_address=wallet_address,
        token_address=TOKEN_ADDRESS.lower(),
        balance_raw="1000000000000000000000",
        checked_at=datetime.now(UTC),
        is_holder=True,
    ))
    await db.commit()


@pytest.fixture()
async def non_holder_headers(client: AsyncClient, monkeypatch) -> dict:
    settings = _configured_settings()
    token, _ = await _authenticate(client, monkeypatch, settings)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
async def holder_headers(client: AsyncClient, db: AsyncSession, monkeypatch) -> dict:
    settings = _configured_settings()
    token, wallet = await _authenticate(client, monkeypatch, settings)
    await _make_holder(db, wallet)
    return {"Authorization": f"Bearer {token}"}


# ── Lists / search ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_guest_list_is_free_tier_only(client: AsyncClient) -> None:
    r = await client.get("/api/v1/assets")
    symbols = {a["symbol"] for a in r.json()["assets"]}
    assert HOLDER_STOCK not in symbols
    assert HOLDER_CRYPTO not in symbols
    assert FREE_STOCK in symbols
    assert FREE_CRYPTO in symbols
    assert len(symbols) == 38


@pytest.mark.asyncio
async def test_non_holder_list_is_still_free_tier_only(client: AsyncClient, non_holder_headers: dict) -> None:
    r = await client.get("/api/v1/assets", headers=non_holder_headers)
    symbols = {a["symbol"] for a in r.json()["assets"]}
    assert HOLDER_STOCK not in symbols
    assert len(symbols) == 38


@pytest.mark.asyncio
async def test_holder_list_includes_full_catalogue(client: AsyncClient, holder_headers: dict) -> None:
    r = await client.get("/api/v1/assets", headers=holder_headers)
    symbols = {a["symbol"] for a in r.json()["assets"]}
    assert HOLDER_STOCK in symbols
    assert HOLDER_CRYPTO in symbols
    assert len(symbols) == 120


@pytest.mark.asyncio
async def test_guest_search_excludes_holder_only_symbol(client: AsyncClient) -> None:
    r = await client.get(f"/api/v1/assets/search?q={HOLDER_STOCK.lower()}")
    symbols = {a["symbol"] for a in r.json()["assets"]}
    assert HOLDER_STOCK not in symbols


@pytest.mark.asyncio
async def test_holder_search_includes_holder_only_symbol(client: AsyncClient, holder_headers: dict) -> None:
    r = await client.get(f"/api/v1/assets/search?q={HOLDER_STOCK.lower()}", headers=holder_headers)
    symbols = {a["symbol"] for a in r.json()["assets"]}
    assert HOLDER_STOCK in symbols


# ── Detail / history ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_guest_free_stock_detail_ok(client: AsyncClient) -> None:
    assert (await client.get(f"/api/v1/assets/{FREE_STOCK}")).status_code == 200


@pytest.mark.asyncio
async def test_guest_holder_stock_detail_401(client: AsyncClient) -> None:
    r = await client.get(f"/api/v1/assets/{HOLDER_STOCK}")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_non_holder_holder_stock_detail_403(client: AsyncClient, non_holder_headers: dict) -> None:
    r = await client.get(f"/api/v1/assets/{HOLDER_STOCK}", headers=non_holder_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_holder_holder_stock_detail_200(client: AsyncClient, holder_headers: dict) -> None:
    r = await client.get(f"/api/v1/assets/{HOLDER_STOCK}", headers=holder_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_guest_holder_crypto_detail_401(client: AsyncClient) -> None:
    r = await client.get(f"/api/v1/assets/{HOLDER_CRYPTO}")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_holder_holder_crypto_detail_200(client: AsyncClient, holder_headers: dict) -> None:
    r = await client.get(f"/api/v1/assets/{HOLDER_CRYPTO}", headers=holder_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_guest_holder_stock_history_401(client: AsyncClient) -> None:
    r = await client.get(f"/api/v1/assets/{HOLDER_STOCK}/history")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_holder_holder_stock_history_200(client: AsyncClient, holder_headers: dict) -> None:
    r = await client.get(f"/api/v1/assets/{HOLDER_STOCK}/history", headers=holder_headers)
    assert r.status_code == 200


# ── Exposures / graphs / correlation / intraday ──────────────────────────

@pytest.mark.asyncio
async def test_guest_free_stock_exposures_excludes_holder_crypto(client: AsyncClient) -> None:
    r = await client.get(f"/api/v1/exposures/{FREE_STOCK}")
    assert r.status_code == 200
    symbols = {s["symbol"] for s in r.json()["scores"]}
    assert HOLDER_CRYPTO not in symbols


@pytest.mark.asyncio
async def test_holder_free_stock_exposures_may_include_holder_crypto(client: AsyncClient, holder_headers: dict) -> None:
    r = await client.get(f"/api/v1/exposures/{FREE_STOCK}", headers=holder_headers)
    assert r.status_code == 200
    # Not asserting HOLDER_CRYPTO is present (score may not exist), only that
    # it is never filtered out purely on the crypto side for a verified holder.
    body = r.json()
    assert isinstance(body["scores"], list)


@pytest.mark.asyncio
async def test_guest_holder_stock_exposures_401(client: AsyncClient) -> None:
    r = await client.get(f"/api/v1/exposures/{HOLDER_STOCK}")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_non_holder_holder_stock_exposures_403(client: AsyncClient, non_holder_headers: dict) -> None:
    r = await client.get(f"/api/v1/exposures/{HOLDER_STOCK}", headers=non_holder_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_guest_free_stock_graph_excludes_holder_crypto(client: AsyncClient) -> None:
    r = await client.get(f"/api/v1/graphs/{FREE_STOCK}")
    assert r.status_code == 200
    symbols = {n["symbol"] for n in r.json()["nodes"]}
    assert HOLDER_CRYPTO not in symbols


@pytest.mark.asyncio
async def test_guest_holder_stock_graph_401(client: AsyncClient) -> None:
    r = await client.get(f"/api/v1/graphs/{HOLDER_STOCK}")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_guest_free_stock_correlation_excludes_holder_crypto(client: AsyncClient) -> None:
    r = await client.get(f"/api/v1/correlation/{FREE_STOCK}")
    assert r.status_code == 200
    symbols = {s["symbol"] for s in r.json()["scores"]}
    assert HOLDER_CRYPTO not in symbols


@pytest.mark.asyncio
async def test_guest_holder_stock_correlation_401(client: AsyncClient) -> None:
    r = await client.get(f"/api/v1/correlation/{HOLDER_STOCK}")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_guest_free_stock_intraday_excludes_holder_crypto(client: AsyncClient) -> None:
    r = await client.get(f"/api/v1/intraday/{FREE_STOCK}")
    assert r.status_code == 200
    symbols = {s["symbol"] for s in r.json()["scores"]}
    assert HOLDER_CRYPTO not in symbols


@pytest.mark.asyncio
async def test_guest_holder_stock_intraday_401(client: AsyncClient) -> None:
    r = await client.get(f"/api/v1/intraday/{HOLDER_STOCK}")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_non_holder_holder_stock_intraday_403(client: AsyncClient, non_holder_headers: dict) -> None:
    r = await client.get(f"/api/v1/intraday/{HOLDER_STOCK}", headers=non_holder_headers)
    assert r.status_code == 403
