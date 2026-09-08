"""Minimal in-process sliding-window rate limiter for auth endpoints.

Keyed by client IP. This is intentionally simple (no Redis dependency) — on
a single Render instance it stops basic nonce-issuance/signature-verification
abuse; if the API ever scales to multiple instances, this should move to a
shared store, but a per-instance limit is still strictly better than none.
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request

_WINDOW_SECONDS = 60.0
_buckets: dict[str, list[float]] = defaultdict(list)


def _client_key(request: Request, scope: str) -> str:
    ip = request.client.host if request.client else "unknown"
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
