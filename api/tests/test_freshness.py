"""Tests for market-session-aware historical freshness (XNYS-calendar-based)."""

from datetime import UTC, date, datetime, timedelta

from app.services.freshness import expected_completed_session, historical_is_stale
from app.services.market_calendar import is_trading_session


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


def test_expected_completed_session_rolls_back_over_a_holiday_friday() -> None:
    """When the Friday recalc deadline itself lands on a market holiday, the
    expected completed session must roll back to the prior real trading
    session, not treat the holiday itself as one."""
    holiday_friday = _find_weekday_holiday(weekday=4)  # Friday
    now = datetime(holiday_friday.year, holiday_friday.month, holiday_friday.day, 23, 30, tzinfo=UTC)

    result = expected_completed_session(now)
    assert result < holiday_friday
    assert is_trading_session(result)
