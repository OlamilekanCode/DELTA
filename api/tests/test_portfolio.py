from app.services.portfolio import TIER_THRESHOLDS, get_tier


def test_tier_boundary_locked_below_50() -> None:
    assert get_tier(4_999) == "locked"


def test_tier_boundary_exactly_50_is_summary() -> None:
    assert get_tier(5_000) == "summary"


def test_tier_boundary_just_under_250_is_summary() -> None:
    assert get_tier(24_999) == "summary"


def test_tier_boundary_exactly_250_is_detailed() -> None:
    assert get_tier(25_000) == "detailed"


def test_tier_boundary_just_under_1000_is_detailed() -> None:
    assert get_tier(99_999) == "detailed"


def test_tier_boundary_exactly_1000_is_premium() -> None:
    assert get_tier(100_000) == "premium"


def test_tier_boundary_well_above_1000_is_premium() -> None:
    assert get_tier(10_000_000) == "premium"


def test_tier_zero_is_locked() -> None:
    assert get_tier(0) == "locked"


def test_thresholds_match_dollar_amounts() -> None:
    assert TIER_THRESHOLDS["summary"] == 5_000  # $50.00
    assert TIER_THRESHOLDS["detailed"] == 25_000  # $250.00
    assert TIER_THRESHOLDS["premium"] == 100_000  # $1,000.00
