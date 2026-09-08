"""Market-aware freshness rules.

Replaces the old fixed 25-hour historical staleness threshold, which
incorrectly flagged data as stale across ordinary weekends and market
holidays. Historical scores follow the Tuesday/Friday recalculation
schedule; crypto quotes and intraday scores follow the actual market clock
(XNYS session + 30-minute bucket), not a flat wall-clock duration.
"""

from datetime import UTC, datetime, timedelta

from app.services.market_calendar import get_market_status

_RECALC_WEEKDAYS = {1, 4}  # Tuesday=1, Friday=4 (Monday=0) — matches the Cloudflare historical cron
_RECALC_HOUR_UTC = 23  # matches "0 23 * * 2,5" — after US market close

_QUOTE_STALE_MINUTES_OPEN = 15
_QUOTE_STALE_MINUTES_CLOSED = 45
_INTRADAY_GRACE_MINUTES = 10


def _aware(ts: datetime) -> datetime:
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=UTC)


def latest_historical_recalc_deadline(now: datetime | None = None) -> datetime:
    """The most recent Tuesday/Friday 23:00 UTC recalculation time that has
    already passed, walking backward from `now` (default: current time)."""
    now = _aware(now or datetime.now(UTC))
    candidate = now.replace(hour=_RECALC_HOUR_UTC, minute=0, second=0, microsecond=0)
    for _ in range(8):
        if candidate.weekday() in _RECALC_WEEKDAYS and candidate <= now:
            return candidate
        candidate -= timedelta(days=1)
    return candidate  # unreachable in practice — 8 days always covers a Tue or Fri


def historical_is_stale(computed_at: datetime | None, now: datetime | None = None) -> bool:
    """Stale if never computed, or computed before the last Tuesday/Friday
    recalculation deadline. Weekends and holidays between recalculations
    never make an up-to-date score look stale."""
    if computed_at is None:
        return True
    return _aware(computed_at) < latest_historical_recalc_deadline(now)


def quote_is_stale(quote_ts: datetime | None, now: datetime | None = None) -> bool:
    """Crypto quote freshness: ~15 min during market hours, ~45 min outside."""
    if quote_ts is None:
        return True
    now = _aware(now or datetime.now(UTC))
    is_open = get_market_status(now).is_open
    threshold = timedelta(minutes=_QUOTE_STALE_MINUTES_OPEN if is_open else _QUOTE_STALE_MINUTES_CLOSED)
    return (now - _aware(quote_ts)) > threshold


def intraday_status(data_ts: datetime | None, now: datetime | None = None) -> str:
    """One of "fresh" | "stale" | "collecting_data" | "market_closed".

    While the market is closed, the last valid live score is always current
    (frozen), never marked stale — the frontend shows a "US market closed"
    pill instead. While open, a score is stale once the expected completed
    30-minute bucket (plus a processing grace window) has passed without a
    newer stored score.
    """
    now = _aware(now or datetime.now(UTC))
    status = get_market_status(now)
    if not status.is_open:
        return "market_closed" if data_ts is not None else "collecting_data"
    if data_ts is None:
        return "collecting_data"
    if status.current_bucket is None:
        return "collecting_data"
    last_completed_bucket = status.current_bucket - timedelta(minutes=30)
    deadline = last_completed_bucket - timedelta(minutes=_INTRADAY_GRACE_MINUTES)
    return "fresh" if _aware(data_ts) >= deadline else "stale"
