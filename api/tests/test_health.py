import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_ok(client: AsyncClient) -> None:
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["demo_mode"] is True
    assert body["db"] in ("ok", "degraded")
    # No Robinhood Chain/router env vars in the test settings and
    # ROUTER_ADAPTERS is empty by default — this must read as
    # "not configured" here, never a false "ready".
    assert body["purchase_verification"]["status"] == "env_not_configured"


@pytest.mark.asyncio
async def test_health_purchase_verification_flags_missing_adapters(client: AsyncClient, monkeypatch) -> None:
    """Env vars alone (no RouterAdapter registered) must report the
    distinct "env_configured_no_adapters" state, not "ready" — this is
    the exact gap that let purchase verification look configured while
    still failing every real attempt."""
    from app.config import Settings

    settings = Settings(
        cors_origins="http://localhost:3000",
        synthex_chain_id=4663,
        robinhood_rpc_url="https://example.invalid/rpc",
        synthex_token_address="0x" + "1" * 40,
        synthex_dex_router_addresses="0x" + "2" * 40,
        synthex_weth_address="0x" + "3" * 40,
    )
    import app.routers.health as health_module
    monkeypatch.setattr(health_module, "get_settings", lambda: settings)
    import app.services.purchase_verification as pv_module
    monkeypatch.setattr(pv_module, "get_settings", lambda: settings)

    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["purchase_verification"]["status"] == "env_configured_no_adapters"
    assert body["purchase_verification"]["env_vars_present"] is True
    assert body["purchase_verification"]["router_adapters_registered"] is False


@pytest.mark.asyncio
async def test_health_returns_503_when_db_check_fails(client: AsyncClient, monkeypatch) -> None:
    """A failed DB check must return a real non-2xx, never status: ok with
    HTTP 200 — Render's health check needs this to detect a dead database."""
    import app.routers.health as health_module

    class _FailingSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def execute(self, *args, **kwargs):
            raise RuntimeError("db down")

    monkeypatch.setattr(health_module, "get_factory", lambda: (lambda: _FailingSession()))

    r = await client.get("/api/v1/health")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    assert body["db"] == "degraded"
