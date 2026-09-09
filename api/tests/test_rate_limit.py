"""services/rate_limit.py — client-IP resolution behind the Vercel BFF.

Every rate-limited endpoint is only ever reached through the Next.js BFF,
so the raw TCP peer address is Vercel's shared egress IP for every request,
not the end user's. _resolve_client_ip must only trust a forwarded IP when
paired with the correct shared secret — never blindly, and never as a
regression when the secret isn't configured.
"""

from starlette.requests import Request

from app.config import Settings
from app.services.rate_limit import _resolve_client_ip


def _make_request(headers: dict[str, str], peer_ip: str = "10.0.0.1") -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (peer_ip, 12345),
    }
    return Request(scope)


def test_forwarded_ip_ignored_without_shared_secret_configured(monkeypatch) -> None:
    import app.services.rate_limit as rl_module
    monkeypatch.setattr(rl_module, "get_settings", lambda: Settings(bff_shared_secret=""))

    request = _make_request({
        "x-bff-shared-secret": "whatever",
        "x-forwarded-client-ip": "203.0.113.5",
    })
    assert _resolve_client_ip(request) == "10.0.0.1"


def test_forwarded_ip_ignored_with_wrong_secret(monkeypatch) -> None:
    import app.services.rate_limit as rl_module
    monkeypatch.setattr(rl_module, "get_settings", lambda: Settings(bff_shared_secret="correct-secret"))

    request = _make_request({
        "x-bff-shared-secret": "wrong-secret",
        "x-forwarded-client-ip": "203.0.113.5",
    })
    assert _resolve_client_ip(request) == "10.0.0.1"


def test_forwarded_ip_trusted_with_correct_secret(monkeypatch) -> None:
    import app.services.rate_limit as rl_module
    monkeypatch.setattr(rl_module, "get_settings", lambda: Settings(bff_shared_secret="correct-secret"))

    request = _make_request({
        "x-bff-shared-secret": "correct-secret",
        "x-forwarded-client-ip": "203.0.113.5",
    })
    assert _resolve_client_ip(request) == "203.0.113.5"


def test_forwarded_ip_falls_back_to_peer_when_header_absent(monkeypatch) -> None:
    import app.services.rate_limit as rl_module
    monkeypatch.setattr(rl_module, "get_settings", lambda: Settings(bff_shared_secret="correct-secret"))

    request = _make_request({"x-bff-shared-secret": "correct-secret"})
    assert _resolve_client_ip(request) == "10.0.0.1"


def test_no_client_falls_back_to_unknown(monkeypatch) -> None:
    import app.services.rate_limit as rl_module
    monkeypatch.setattr(rl_module, "get_settings", lambda: Settings())

    scope = {"type": "http", "headers": [], "client": None}
    request = Request(scope)
    assert _resolve_client_ip(request) == "unknown"
