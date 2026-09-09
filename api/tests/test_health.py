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
