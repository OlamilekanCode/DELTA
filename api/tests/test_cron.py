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


_FULLY_FAILED_COUNTS = {"requested": 20, "succeeded": 0, "skipped": 0, "failed": 20, "records_written": 0}
_DEMO_SKIPPED_COUNTS = {"requested": 0, "succeeded": 0, "skipped": 1, "failed": 0, "records_written": 0}


@pytest.mark.asyncio
async def test_cron_history_includes_cleanup_counts(client: AsyncClient, monkeypatch) -> None:
    """The endpoint must actually call cleanup and surface its counts, not
    just claim to in its docstring."""
    import app.routers.cron as cron_module

    async def fake_cleanup() -> dict:
        return {"intraday_prices_deleted": 3, "crypto_quote_observations_deleted": 7}

    monkeypatch.setattr(cron_module, "cmd_cleanup_old_data", fake_cleanup)
    resp = await client.post("/api/v1/cron/refresh-history-and-scores", headers={"x-cron-secret": _SECRET})
    assert resp.status_code == 200
    assert resp.json()["cleanup"] == {"intraday_prices_deleted": 3, "crypto_quote_observations_deleted": 7}


@pytest.mark.asyncio
async def test_cron_history_returns_502_when_stock_side_totally_fails(client: AsyncClient, monkeypatch) -> None:
    """Crypto history can refresh fine while Marketstack is completely down —
    that must never recompute scores from fresh crypto against stale stock
    prices, and must be reported as a genuine failure on its own (not
    silently 200 just because crypto succeeded)."""
    import app.routers.cron as cron_module

    async def fake_stock(**kwargs) -> dict:
        return dict(_FULLY_FAILED_COUNTS)

    async def fake_crypto() -> dict:
        return dict(_DEMO_SKIPPED_COUNTS)

    async def fail_if_called() -> int:
        raise AssertionError("cmd_recompute_scores must not be called when stock ingestion totally failed")

    monkeypatch.setattr(cron_module, "cmd_refresh_stock_eod", fake_stock)
    monkeypatch.setattr(cron_module, "cmd_refresh_crypto_history", fake_crypto)
    monkeypatch.setattr(cron_module, "cmd_recompute_scores", fail_if_called)

    resp = await client.post("/api/v1/cron/refresh-history-and-scores", headers={"x-cron-secret": _SECRET})
    assert resp.status_code == 502
    detail = resp.json()["detail"]
    assert detail["failed_side"] == "stock_eod"
    assert detail["scores_skipped_reason"] == "stock_eod_failed"
    assert "cleanup" in detail  # cleanup still ran despite the failure


@pytest.mark.asyncio
async def test_cron_history_returns_502_when_crypto_side_totally_fails(client: AsyncClient, monkeypatch) -> None:
    """The same must hold when crypto (not stock) is the side that's
    completely down — do not require both sides to fail."""
    import app.routers.cron as cron_module

    async def fake_stock(**kwargs) -> dict:
        return dict(_DEMO_SKIPPED_COUNTS)

    async def fake_crypto() -> dict:
        return dict(_FULLY_FAILED_COUNTS)

    async def fail_if_called() -> int:
        raise AssertionError("cmd_recompute_scores must not be called when crypto ingestion totally failed")

    monkeypatch.setattr(cron_module, "cmd_refresh_stock_eod", fake_stock)
    monkeypatch.setattr(cron_module, "cmd_refresh_crypto_history", fake_crypto)
    monkeypatch.setattr(cron_module, "cmd_recompute_scores", fail_if_called)

    resp = await client.post("/api/v1/cron/refresh-history-and-scores", headers={"x-cron-secret": _SECRET})
    assert resp.status_code == 502
    detail = resp.json()["detail"]
    assert detail["failed_side"] == "crypto_history"
    assert detail["scores_skipped_reason"] == "crypto_history_failed"


@pytest.mark.asyncio
async def test_cron_history_returns_502_when_both_sides_totally_fail(client: AsyncClient, monkeypatch) -> None:
    import app.routers.cron as cron_module

    async def fake_stock(**kwargs) -> dict:
        return dict(_FULLY_FAILED_COUNTS)

    async def fake_crypto() -> dict:
        return dict(_FULLY_FAILED_COUNTS)

    monkeypatch.setattr(cron_module, "cmd_refresh_stock_eod", fake_stock)
    monkeypatch.setattr(cron_module, "cmd_refresh_crypto_history", fake_crypto)

    resp = await client.post("/api/v1/cron/refresh-history-and-scores", headers={"x-cron-secret": _SECRET})
    assert resp.status_code == 502
    detail = resp.json()["detail"]
    assert detail["failed_side"] == "stock_eod_and_crypto_history"
    assert "cleanup" in detail  # cleanup still ran and is visible even on hard failure


@pytest.mark.asyncio
async def test_cron_history_unexpected_exception_never_leaks_message(client: AsyncClient, monkeypatch) -> None:
    """An unexpected exception must return a generic 5xx without echoing the
    raw exception text back to the caller."""
    import app.routers.cron as cron_module

    secret_looking_message = "boom: MARKETSTACK_API_KEY=super-secret-value-123"

    async def fake_stock(**kwargs) -> dict:
        raise ValueError(secret_looking_message)

    monkeypatch.setattr(cron_module, "cmd_refresh_stock_eod", fake_stock)
    resp = await client.post("/api/v1/cron/refresh-history-and-scores", headers={"x-cron-secret": _SECRET})
    assert resp.status_code == 502
    assert "super-secret-value-123" not in resp.text
    assert resp.json()["detail"]["error"] == "internal_error"


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
