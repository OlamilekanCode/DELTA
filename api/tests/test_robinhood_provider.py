"""providers/robinhood.py — _parse_active fails closed on anything ambiguous.

A token's "active" status must never default to True by accident: a real
bool is trusted, a string is parsed for "true"/"false" explicitly (Python's
own bool("false") is True, which would silently treat an explicit
"active": "false" as active), and a missing/empty status never defaults to
active.
"""

from app.providers.robinhood import _parse_active


def test_bool_true_is_trusted() -> None:
    assert _parse_active(True, "") is True


def test_bool_false_is_trusted() -> None:
    assert _parse_active(False, "active") is False


def test_string_false_is_not_truthy() -> None:
    """Python's bool("false") is True — this must not leak through."""
    assert _parse_active("false", "") is False


def test_string_true_is_active() -> None:
    assert _parse_active("true", "") is True


def test_missing_active_falls_back_to_status_active() -> None:
    assert _parse_active(None, "active") is True


def test_missing_active_falls_back_to_status_live() -> None:
    assert _parse_active(None, "live") is True


def test_missing_active_and_empty_status_defaults_inactive() -> None:
    """Both `active` and `status`/`state` absent must fail closed
    (inactive), never default to active."""
    assert _parse_active(None, "") is False


def test_missing_active_unrecognized_status_is_inactive() -> None:
    assert _parse_active(None, "delisted") is False


def test_unrecognized_string_value_falls_back_to_status() -> None:
    assert _parse_active("unknown", "active") is True
    assert _parse_active("unknown", "") is False
