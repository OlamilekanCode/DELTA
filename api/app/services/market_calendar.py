"""US equity market status via the maintained `exchange_calendars` XNYS calendar.

Handles regular holidays, early closes and DST transitions correctly instead of
a hand-maintained holiday list.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime

import exchange_calendars as xcals
import pandas as pd

MARKET_TIMEZONE = "America/New_York"
_BUCKET_MINUTES = 30

_calendar = xcals.get_calendar("XNYS")


@dataclass
class MarketStatus:
    is_open: bool
    timezone: str
    last_close: datetime
    next_open: datetime
    current_bucket: datetime | None
    status_reason: str


def _floor_to_bucket(ts: pd.Timestamp) -> datetime:
    floored_minute = (ts.minute // _BUCKET_MINUTES) * _BUCKET_MINUTES
    return ts.replace(minute=floored_minute, second=0, microsecond=0, nanosecond=0).to_pydatetime()


def get_market_status(now: datetime | None = None) -> MarketStatus:
    ts = pd.Timestamp(now or datetime.now(UTC))
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")

    is_open = bool(_calendar.is_open_on_minute(ts, ignore_breaks=True))
    last_close = _calendar.previous_close(ts).to_pydatetime()
    next_open = _calendar.next_open(ts).to_pydatetime()

    if is_open:
        current_bucket = _floor_to_bucket(ts)
        status_reason = "regular trading hours"
    else:
        current_bucket = None
        session_date = ts.tz_convert(None).normalize()
        if _calendar.is_session(session_date):
            status_reason = "outside regular trading hours"
        else:
            status_reason = "market holiday or weekend"

    return MarketStatus(
        is_open=is_open,
        timezone=MARKET_TIMEZONE,
        last_close=last_close,
        next_open=next_open,
        current_bucket=current_bucket,
        status_reason=status_reason,
    )


def recent_session_dates(now: datetime | None = None, count: int = 20) -> list[date]:
    """The most recent `count` completed-or-in-progress trading session dates, oldest first."""
    ts = pd.Timestamp(now or datetime.now(UTC))
    normalized = (ts.tz_convert(None) if ts.tzinfo else ts).normalize()
    start = normalized - pd.Timedelta(days=count * 3)  # buffer for weekends/holidays
    sessions = _calendar.sessions_in_range(start, normalized)
    return [s.date() for s in sessions[-count:]]


def upcoming_session_dates(now: datetime | None = None, count: int = 5) -> list[date]:
    """The next `count` trading session dates strictly after `now`, ascending."""
    ts = pd.Timestamp(now or datetime.now(UTC))
    normalized = (ts.tz_convert(None) if ts.tzinfo else ts).normalize()
    end = normalized + pd.Timedelta(days=count * 3 + 5)  # buffer for weekends/holidays
    sessions = _calendar.sessions_in_range(normalized + pd.Timedelta(days=1), end)
    return [s.date() for s in sessions[:count]]


def session_open_close(session_date: date) -> tuple[datetime, datetime]:
    """UTC (open, close) datetimes for a given NYSE trading session date."""
    session = pd.Timestamp(session_date)
    return (
        _calendar.session_open(session).to_pydatetime(),
        _calendar.session_close(session).to_pydatetime(),
    )
