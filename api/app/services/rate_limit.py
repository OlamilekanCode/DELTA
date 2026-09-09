"""Minimal in-process sliding-window rate limiter for auth endpoints.

Keyed by client IP. This is intentionally simple (no Redis dependency) — on
a single Render instance it stops basic nonce-issuance/signature-verification
abuse; if the API ever scales to multiple instances, this should move to a
shared store, but a per-instance limit is still strictly better than none.

Every endpoint that calls enforce_rate_limit() is reached through the
Next.js BFF (browser -> Vercel route handler -> this API), so the raw TCP
peer address is Vercel's shared egress IP for every single request, not
the end user's — bucketing by it would let one busy user (or several
concurrent ones) trip the limit for everyone else. See _resolve_client_ip.
"""

import hmac
import time
from collections import defaultdict

from fastapi import HTTPException, Request

from app.config import get_settings

_WINDOW_SECONDS = 60.0
_buckets: dict[str, list[float]] = defaultdict(list)


def _resolve_client_ip(request: Request) -> str:
    """The real end-user IP when it can be trusted, otherwise the raw TCP
    peer address. X-Forwarded-Client-IP is only trusted when it's paired
    with the correct X-BFF-Shared-Secret header — a value an outside
    caller hitting this API directly (bypassing the BFF) cannot produce,
    since it's never exposed to the browser. Without BFF_SHARED_SECRET
    configured, the header is never trusted at all (same as before)."""
    settings = get_settings()
    secret = settings.bff_shared_secret
    if secret:
        provided = request.headers.get("x-bff-shared-secret", "")
        if hmac.compare_digest(provided, secret):
            forwarded = request.headers.get("x-forwarded-client-ip")
            if forwarded:
                return forwarded.strip()
    return request.client.host if request.client else "unknown"


def _client_key(request: Request, scope: str) -> str:
    ip = _resolve_client_ip(request)
    return f"{scope}:{ip}"


def enforce_rate_limit(request: Request, scope: str, max_requests: int) -> None:
    key = _client_key(request, scope)
    now = time.monotonic()
    window_start = now - _WINDOW_SECONDS
    hits = [t for t in _buckets[key] if t > window_start]
    if len(hits) >= max_requests:
        raise HTTPException(status_code=429, detail="rate_limited")
    hits.append(now)
    _buckets[key] = hits


def reset_rate_limits() -> None:
    """Test-only helper to clear all buckets between test runs."""
    _buckets.clear()
