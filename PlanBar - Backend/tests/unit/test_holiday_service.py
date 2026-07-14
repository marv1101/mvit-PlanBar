from datetime import date

from app.services.holiday_service import (
    _FIXED_NATIONWIDE,
    _HAS_HOLIDAYS,
    _get_fixed_holidays,
    get_german_holidays,
)


def test_get_german_holidays_neujahr():
    """New Year's Day is a fixed nationwide holiday."""
    result = get_german_holidays(date(2024, 1, 1), date(2024, 1, 10))
    assert "2024-01-01" in result


def test_get_german_holidays_sorted():
    """Result must be sorted chronologically."""
    result = get_german_holidays(date(2024, 1, 1), date(2024, 12, 31))
    assert result == sorted(result)


# The following tests require python-holidays (movable holidays + subdivisions)
# They are skipped when the library is not installed (e.g. CI with Python 3.14).


def test_get_german_holidays_epiphany_with_subdivision():
    """Baden-Württemberg includes Epiphany (Jan 6)."""
    if not _HAS_HOLIDAYS:
        return  # skip when library unavailable
    result = get_german_holidays(date(2024, 1, 1), date(2024, 1, 10), subdivision="BW")
    assert "2024-01-01" in result
    assert "2024-01-06" in result


def test_get_german_holidays_easter():
    """Easter Monday is a movable nationwide holiday."""
    if not _HAS_HOLIDAYS:
        return  # skip when library unavailable
    result = get_german_holidays(date(2024, 3, 25), date(2024, 4, 5))
    assert "2024-04-01" in result


def test_fallback_fixed_holidays():
    """Fallback returns only fixed nationwide holidays."""
    result = _get_fixed_holidays(date(2024, 1, 1), date(2024, 12, 31))
    for d in result:
        dt = date.fromisoformat(d)
        assert (dt.month, dt.day) in _FIXED_NATIONWIDE
    assert len(result) == len(_FIXED_NATIONWIDE)
