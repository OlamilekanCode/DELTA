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


@pytest.mark.asyncio
async def test_cron_refresh_intraday_ok(client: AsyncClient) -> None:
    """With USE_DEMO_DATA=true, cmd_refresh_intraday() skips immediately —
    this tests authentication, routing and the distinct advisory lock."""
    resp = await client.post(
        "/api/v1/cron/refresh-intraday",
        headers={"x-cron-secret": _SECRET},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["command"] == "refresh-intraday"


@pytest.mark.asyncio
async def test_cron_intraday_no_secret_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/cron/refresh-intraday")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cron_refresh_intraday_degraded_when_marketstack_fails(client: AsyncClient, monkeypatch) -> None:
    """Crypto candles can build fine from already-stored observations while
    Marketstack is completely down — that must never read as success."""
    import app.routers.cron as cron_module

    async def fake_refresh_intraday() -> dict:
        return {
            "requested": 20, "succeeded": 5, "skipped": 0, "failed": 20,
            "marketstack_failed": True, "score_pairs_recomputed": 0,
            "score_stocks_recomputed": 0, "score_stocks_failed": 0,
        }

    monkeypatch.setattr(cron_module, "cmd_refresh_intraday", fake_refresh_intraday)
    resp = await client.post("/api/v1/cron/refresh-intraday", headers={"x-cron-secret": _SECRET})
    assert resp.status_code == 502
    assert resp.json()["detail"]["reason"] == "no_intraday_scores_recomputed"


@pytest.mark.asyncio
async def test_cron_refresh_intraday_degraded_when_no_scores_recomputed(client: AsyncClient, monkeypatch) -> None:
    """Candle ingestion can succeed while every stock's score recomputation
    itself fails — that is a real failure even though counts["succeeded"] > 0."""
    import app.routers.cron as cron_module

    async def fake_refresh_intraday() -> dict:
        return {
            "requested": 20, "succeeded": 20, "skipped": 0, "failed": 0,
            "marketstack_failed": False, "score_pairs_recomputed": 0,
            "score_stocks_recomputed": 0, "score_stocks_failed": 20,
        }

    monkeypatch.setattr(cron_module, "cmd_refresh_intraday", fake_refresh_intraday)
    resp = await client.post("/api/v1/cron/refresh-intraday", headers={"x-cron-secret": _SECRET})
    assert resp.status_code == 502
    assert resp.json()["detail"]["reason"] == "no_intraday_scores_recomputed"


@pytest.mark.asyncio
async def test_cron_refresh_intraday_ok_when_pairs_still_collecting(client: AsyncClient, monkeypatch) -> None:
    """A legitimate early-launch state — every pair still below the
    alignment threshold — must never be reported as a job failure."""
    import app.routers.cron as cron_module

    async def fake_refresh_intraday() -> dict:
        return {
            "requested": 20, "succeeded": 20, "skipped": 0, "failed": 0,
            "marketstack_failed": False, "score_pairs_recomputed": 0,
            "score_stocks_recomputed": 20, "score_stocks_failed": 0,
        }

    monkeypatch.setattr(cron_module, "cmd_refresh_intraday", fake_refresh_intraday)
    resp = await client.post("/api/v1/cron/refresh-intraday", headers={"x-cron-secret": _SECRET})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
