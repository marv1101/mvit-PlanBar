from datetime import date

import pytest
from app.services.holiday_service import (
    _FIXED_NATIONWIDE,
    _HAS_HOLIDAYS,
    _get_fixed_holidays,
    get_german_holidays,
)

# ---------------------------------------------------------------------------
# Core nationwide / movable holidays
# ---------------------------------------------------------------------------


def test_get_german_holidays_neujahr():
    """New Year's Day is a fixed nationwide holiday."""
    result = get_german_holidays(date(2024, 1, 1), date(2024, 1, 10))
    assert "2024-01-01" in result


def test_get_german_holidays_sorted():
    """Result must be sorted chronologically."""
    result = get_german_holidays(date(2024, 1, 1), date(2024, 12, 31))
    assert result == sorted(result)


def test_get_german_holidays_returns_only_iso_strings():
    """Every returned entry must be an ISO-format date string."""
    result = get_german_holidays(date(2024, 1, 1), date(2024, 12, 31))
    for d in result:
        # Should be parseable as ISO date
        date.fromisoformat(d)


def test_get_german_holidays_no_holiday_in_range():
    """Returns an empty list for a range with no public holidays."""
    # A random 5-day window in March (no fixed nationwide holiday, no movable
    # holiday in 2024 between 11-15 March).
    result = get_german_holidays(date(2024, 3, 11), date(2024, 3, 15))
    assert result == []


# ---------------------------------------------------------------------------
# Movable holidays + subdivisions (require python-holidays)
# ---------------------------------------------------------------------------


def test_get_german_holidays_epiphany_with_subdivision():
    """Baden-Württemberg includes Epiphany (Jan 6)."""
    if not _HAS_HOLIDAYS:
        pytest.skip("python-holidays not installed")
    result = get_german_holidays(
        date(2024, 1, 1), date(2024, 1, 10), subdivision="BW"
    )
    assert "2024-01-01" in result
    assert "2024-01-06" in result


def test_get_german_holidays_easter():
    """Easter Monday is a movable nationwide holiday."""
    if not _HAS_HOLIDAYS:
        pytest.skip("python-holidays not installed")
    result = get_german_holidays(date(2024, 3, 25), date(2024, 4, 5))
    assert "2024-04-01" in result


def test_get_german_holidays_nrw_includes_all_saints():
    """NRW (Nordrhein-Westfalen) includes Allerheiligen (Nov 1)."""
    if not _HAS_HOLIDAYS:
        pytest.skip("python-holidays not installed")
    result = get_german_holidays(
        date(2024, 10, 25), date(2024, 11, 5), subdivision="NW"
    )
    # Reformation Day is NOT in NRW; Allerheiligen IS in NRW
    assert "2024-11-01" in result
    assert "2024-10-31" not in result


def test_get_german_holidays_by_includes_epiphany():
    """Bayern (BY) includes Epiphany (Jan 6) — state-specific."""
    if not _HAS_HOLIDAYS:
        pytest.skip("python-holidays not installed")
    result = get_german_holidays(
        date(2024, 1, 1), date(2024, 1, 10), subdivision="BY"
    )
    assert "2024-01-06" in result


def test_get_german_holidays_be_includes_womens_day():
    """Berlin (BE) includes International Women's Day (Mar 8) — state-specific."""
    if not _HAS_HOLIDAYS:
        pytest.skip("python-holidays not installed")
    result = get_german_holidays(
        date(2024, 3, 1), date(2024, 3, 15), subdivision="BE"
    )
    assert "2024-03-08" in result


# ---------------------------------------------------------------------------
# Year-boundary edge cases
# ---------------------------------------------------------------------------


def test_get_german_holidays_year_boundary_dec_31_to_jan_1():
    """Year-boundary: 2024-12-31 to 2025-01-02 includes both years' New Year."""
    result = get_german_holidays(date(2024, 12, 30), date(2025, 1, 2))
    assert "2025-01-01" in result
    # 2024-01-01 is outside the requested range
    assert "2024-01-01" not in result


def test_get_german_holidays_single_day_range():
    """A single-day range still returns holidays for that day."""
    result = get_german_holidays(date(2024, 1, 1), date(2024, 1, 1))
    assert "2024-01-01" in result


def test_get_german_holidays_inclusive_end_date():
    """end_date is inclusive (not exclusive)."""
    result = get_german_holidays(date(2024, 1, 1), date(2024, 1, 1))
    assert "2024-01-01" in result
    # 2024-01-02 not included
    assert "2024-01-02" not in result


def test_get_german_holidays_leap_year():
    """Schaltjahr-Behandlung: 2024 ist ein Schaltjahr — der Algorithmus
    iteriert korrekt über den 29. Februar."""
    # 2024-02-29 exists; 2024-03-01 should be checked too
    result = get_german_holidays(date(2024, 2, 28), date(2024, 3, 1))
    # No fixed nationwide holiday in this range, so empty (movable ones
    # like Karfreitag 2024-03-29 are out of range)
    assert "2024-02-29" not in result
    assert "2024-03-01" not in result


# ---------------------------------------------------------------------------
# Fallback path
# ---------------------------------------------------------------------------


def test_fallback_fixed_holidays():
    """Fallback returns only fixed nationwide holidays."""
    result = _get_fixed_holidays(date(2024, 1, 1), date(2024, 12, 31))
    for d in result:
        dt = date.fromisoformat(d)
        assert (dt.month, dt.day) in _FIXED_NATIONWIDE
    assert len(result) == len(_FIXED_NATIONWIDE)


def test_fallback_fixed_holidays_exact_matches():
    """Fallback returns exactly the 5 fixed nationwide holidays for 2024."""
    result = _get_fixed_holidays(date(2024, 1, 1), date(2024, 12, 31))
    expected = {
        "2024-01-01",  # Neujahr
        "2024-05-01",  # Tag der Arbeit
        "2024-10-03",  # Tag der Deutschen Einheit
        "2024-12-25",  # 1. Weihnachtstag
        "2024-12-26",  # 2. Weihnachtstag
    }
    assert set(result) == expected


def test_fallback_fixed_holidays_includes_christmas():
    """Fallback must include both Christmas days."""
    result = _get_fixed_holidays(date(2024, 12, 1), date(2024, 12, 31))
    assert "2024-12-25" in result
    assert "2024-12-26" in result


def test_fallback_fixed_holidays_empty_when_outside_all_dates():
    """Returns empty list for a range without any fixed nationwide holiday."""
    result = _get_fixed_holidays(date(2024, 3, 1), date(2024, 3, 31))
    assert result == []


def test_fallback_fixed_holidays_inclusive_end():
    """end_date is inclusive in fallback path too."""
    result = _get_fixed_holidays(date(2024, 1, 1), date(2024, 1, 1))
    assert "2024-01-01" in result


def test_fallback_fixed_holidays_year_boundary():
    """Fallback across year boundary still includes 2025-01-01 only."""
    result = _get_fixed_holidays(date(2024, 12, 30), date(2025, 1, 5))
    assert "2025-01-01" in result
    assert "2024-12-25" not in result  # outside range
    assert "2025-05-01" not in result  # outside range
