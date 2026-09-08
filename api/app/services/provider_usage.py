"""Structured provider-usage logging so actual API call volume can be compared
against the prelaunch credit budget. Never logs API keys or other secrets —
only provider name, endpoint, and small non-sensitive metadata (symbol counts,
not the symbols' underlying request payloads).
"""

import logging

log = logging.getLogger("provider_usage")


def log_provider_call(provider: str, endpoint: str, **meta: object) -> None:
    details = " ".join(f"{k}={v}" for k, v in meta.items())
    log.info("provider_call provider=%s endpoint=%s %s", provider, endpoint, details)
