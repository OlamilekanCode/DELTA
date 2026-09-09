"""Tests for market-session-aware historical freshness (XNYS-calendar-based)."""

from datetime import UTC, date, datetime, timedelta

from app.services.freshness import expected_completed_session, historical_is_stale, intraday_status
from app.services.market_calendar import get_market_status, is_trading_session


def _find_weekday_holiday(weekday: int, start_year: int = 2020, end_year: int = 2032) -> date:
    """A real XNYS holiday landing on the given weekday, found via the
    actual calendar rather than a hardcoded/guessed date."""
    d = date(start_year, 1, 1)
    end = date(end_year, 1, 1)
    while d < end:
        if d.weekday() == weekday and not is_trading_session(d):
            return d
        d += timedelta(days=1)
    raise AssertionError(f"no holiday found for weekday={weekday} in {start_year}-{end_year}")


def test_historical_is_stale_none_data_ts_is_stale() -> None:
    assert historical_is_stale(None) is True


def test_historical_is_stale_true_for_old_data_ts() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    old_data_ts = datetime(2026, 8, 1, tzinfo=UTC)
    assert historical_is_stale(old_data_ts, now=now) is True


def test_historical_is_stale_false_when_data_ts_matches_expected_session() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    expected = expected_completed_session(now)
    fresh_data_ts = datetime(expected.year, expected.month, expected.day, tzinfo=UTC)
    assert historical_is_stale(fresh_data_ts, now=now) is False


def test_historical_is_stale_accepts_bare_date() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    expected = expected_completed_session(now)
    assert historical_is_stale(expected, now=now) is False
    assert historical_is_stale(expected - timedelta(days=30), now=now) is True


def test_historical_is_stale_naive_data_ts_treated_as_utc() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    expected = expected_completed_session(now)
    naive_fresh = datetime(expected.year, expected.month, expected.day)  # no tzinfo
    assert historical_is_stale(naive_fresh, now=now) is False


def test_expected_completed_session_is_always_a_real_trading_session() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    assert is_trading_session(expected_completed_session(now))


def test_intraday_status_market_closed_none_data_ts_is_collecting_data() -> None:
    # Saturday — market closed.
    now = datetime.fromisoformat("2026-09-12T15:00:00+00:00")
    assert intraday_status(None, now=now) == "collecting_data"


def test_intraday_status_market_closed_recent_score_is_current() -> None:
    now = datetime.fromisoformat("2026-09-12T15:00:00+00:00")  # Saturday
    status = get_market_status(now)
    assert intraday_status(status.last_close, now=now) == "market_closed"


def test_intraday_status_market_closed_prior_session_stale_after_grace_elapses() -> None:
    """The PRIOR session must only be tolerated for a short grace window
    right after the most recent close — not for the entire time the
    market happens to stay closed afterward. A score from the session
    BEFORE last_close, checked well after that grace has elapsed, must
    read as stale even though the market is still closed."""
    now = datetime.fromisoformat("2026-09-12T15:00:00+00:00")  # Saturday
    status = get_market_status(now)
    from app.services.market_calendar import previous_trading_session
    prior_session_close = get_market_status(
        datetime.combine(previous_trading_session(status.last_close.date()), datetime.min.time(), tzinfo=UTC)
    ).last_close
    assert intraday_status(prior_session_close, now=now) == "stale"


def test_intraday_status_market_closed_weeks_old_score_is_stale() -> None:
    """A "market_closed" score must never be accepted regardless of age —
    a broken intraday job from weeks ago must read as stale, not as
    "current, just frozen for the weekend"."""
    now = datetime.fromisoformat("2026-09-12T15:00:00+00:00")  # Saturday
    weeks_old = now - timedelta(days=21)
    assert intraday_status(weeks_old, now=now) == "stale"


def test_expected_completed_session_rolls_back_over_a_holiday_friday() -> None:
    """When the Friday recalc deadline itself lands on a market holiday, the
    expected completed session must roll back to the prior real trading
    session, not treat the holiday itself as one."""
    holiday_friday = _find_weekday_holiday(weekday=4)  # Friday
    now = datetime(holiday_friday.year, holiday_friday.month, holiday_friday.day, 23, 30, tzinfo=UTC)

    result = expected_completed_session(now)
    assert result < holiday_friday
    assert is_trading_session(result)
