"""US equity market status via the maintained `exchange_calendars` XNYS calendar.

Handles regular holidays, early closes and DST transitions correctly instead of
a hand-maintained holiday list.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

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
