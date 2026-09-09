"""Market-aware freshness rules.

Replaces the old fixed 25-hour historical staleness threshold, which
incorrectly flagged data as stale across ordinary weekends and market
holidays. Historical scores follow the Tuesday/Friday recalculation
schedule; crypto quotes and intraday scores follow the actual market clock
(XNYS session + 30-minute bucket), not a flat wall-clock duration.
"""

from datetime import UTC, date, datetime, timedelta

from app.services.market_calendar import (
    get_market_status,
    is_trading_session,
    previous_trading_session,
)

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


def expected_completed_session(now: datetime | None = None) -> date:
    """The most recent XNYS trading session date that should already be
    reflected in stored historical data, given the last Tuesday/Friday
    23:00 UTC recalculation deadline that has passed. Uses the actual
    exchange calendar (not a flat weekday check) so a holiday landing on a
    Tuesday or Friday correctly rolls back to the prior real session."""
    deadline = latest_historical_recalc_deadline(now)
    deadline_date = deadline.astimezone(UTC).date()
    if is_trading_session(deadline_date):
        return deadline_date
    return previous_trading_session(deadline_date)


def historical_is_stale(data_ts: datetime | date | None, now: datetime | None = None) -> bool:
    """Stale if there is no data timestamp at all, or its trading-session
    date is older than the most recent session the last Tuesday/Friday job
    should already have captured — comparing the underlying market DATA's
    timestamp, never just the calculation's wall-clock `computed_at`.
    Recomputing against unchanged, already-stale prices must not make
    stale market data look fresh just because the job happened to run.
    Weekends and holidays between recalculations never make genuinely
    up-to-date data look stale.
    """
    if data_ts is None:
        return True
    data_date = data_ts.date() if isinstance(data_ts, datetime) else data_ts
    return data_date < expected_completed_session(now)


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
    # The grace window starts when the bucket actually closes (at
    # status.current_bucket, the instant the new bucket began), not 10
    # minutes before it. Subtracting the grace from last_completed_bucket
    # instead made the deadline a fixed 20 minutes before the completed
    # bucket regardless of how much time had actually passed since it
    # closed — so a score still reflecting the *previous* bucket read as
    # stale the instant a new bucket closed, before any grace had elapsed.
    grace_expires_at = status.current_bucket + timedelta(minutes=_INTRADAY_GRACE_MINUTES)
    deadline = last_completed_bucket if now >= grace_expires_at else last_completed_bucket - timedelta(minutes=30)
    return "fresh" if _aware(data_ts) >= deadline else "stale"
