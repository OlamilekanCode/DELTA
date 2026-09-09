"""recent_session_dates() must never return a session whose open is still
in the future — before 9:30 ET on a trading day, "today" hasn't started
yet, and the most recent *completed-or-in-progress* session is still
yesterday's."""

from datetime import date, timedelta

from app.services.market_calendar import recent_session_dates, session_open_close

# 2024-01-10 is a Wednesday, a regular NYSE trading session with no holiday
# on either side (2024-01-09 Tuesday is the prior session).
_TRADING_DAY = date(2024, 1, 10)
_PRIOR_SESSION = date(2024, 1, 9)


def test_recent_session_dates_excludes_todays_session_before_market_open() -> None:
    session_open, _ = session_open_close(_TRADING_DAY)
    before_open = session_open - timedelta(hours=1)
    result = recent_session_dates(before_open, count=1)
    assert result == [_PRIOR_SESSION]


def test_recent_session_dates_includes_todays_session_after_market_open() -> None:
    session_open, _ = session_open_close(_TRADING_DAY)
    after_open = session_open + timedelta(minutes=1)
    result = recent_session_dates(after_open, count=1)
    assert result == [_TRADING_DAY]


def test_recent_session_dates_1w_does_not_drop_a_completed_session_before_open() -> None:
    session_open, _ = session_open_close(_TRADING_DAY)
    before_open = session_open - timedelta(hours=1)
    result = recent_session_dates(before_open, count=5)
    assert result[-1] == _PRIOR_SESSION
    assert _TRADING_DAY not in result
    assert len(result) == 5


def test_recent_session_dates_exact_open_instant_counts_as_started() -> None:
    session_open, _ = session_open_close(_TRADING_DAY)
    result = recent_session_dates(session_open, count=1)
    assert result == [_TRADING_DAY]
