"""Tests for the protected /cron/* endpoints."""

import pytest
from httpx import AsyncClient

_SECRET = "test-cron-secret-xyz"


@pytest.mark.asyncio
async def test_cron_no_secret_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/cron/refresh-crypto-quotes")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cron_wrong_secret_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/cron/refresh-crypto-quotes",
        headers={"x-cron-secret": "totally-wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cron_empty_secret_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/cron/refresh-crypto-quotes",
        headers={"x-cron-secret": ""},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cron_refresh_crypto_quotes_ok(client: AsyncClient) -> None:
    """With a valid secret the endpoint returns ok=True.

    With USE_DEMO_DATA=true the command logs a skip message and returns
    immediately — this tests authentication and routing, not live provider calls.
    """
    resp = await client.post(
        "/api/v1/cron/refresh-crypto-quotes",
        headers={"x-cron-secret": _SECRET},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["command"] == "refresh-crypto-quotes"


@pytest.mark.asyncio
async def test_cron_refresh_history_and_scores_ok(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/cron/refresh-history-and-scores",
        headers={"x-cron-secret": _SECRET},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["command"] == "refresh-history-and-scores"


@pytest.mark.asyncio
async def test_cron_history_no_secret_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/cron/refresh-history-and-scores")
    assert resp.status_code == 401
