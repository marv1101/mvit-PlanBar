"""Tests for ArbZG (Arbeitszeitgesetz) compliance validator."""

from datetime import date, time, timedelta

from app.services.arbzg_validator import (
    validate_breaks,
    validate_consecutive_days,
    validate_max_daily_hours,
    validate_rest_time,
    validate_schedule,
)


def _shift(
    employee_id: int,
    start_date: date,
    start_time: time,
    end_date: date,
    end_time: time,
    break_start: str | None = None,
    break_end: str | None = None,
) -> dict:
    """Helper to build a shift dict matching Shiftplan fields."""
    return {
        "employee_id": employee_id,
        "date": start_date,
        "start_time": start_time,
        "end_date": end_date,
        "end_time": end_time,
        "break_start": break_start,
        "break_end": break_end,
    }


# ── test_valid_schedule_passes ──────────────────────────────────────────────
class TestValidSchedulePasses:
    def test_normal_schedule_no_violations(self):
        """A schedule with proper rest times and breaks should pass.

        Two employees each working up to 5 consecutive days, with at
        least 11h rest between shifts and proper breaks.
        """
        d = date(2025, 7, 1)
        # Employee 1: 5 consecutive workdays, 8h each with 30 min break
        emp1_shifts = [
            _shift(1, d + timedelta(days=i), time(8, 0), d + timedelta(days=i), time(16, 0), "12:00", "12:30")
            for i in range(5)
        ]
        # Employee 2: 5 consecutive workdays, 7.5h each with 30 min break
        emp2_shifts = [
            _shift(2, d + timedelta(days=i), time(6, 0), d + timedelta(days=i), time(13, 30), "10:00", "10:30")
            for i in range(5)
        ]

        schedule = {}
        for i in range(5):
            day = d + timedelta(days=i)
            day_shifts = []
            # Find shifts starting on this day for each employee
            for s in emp1_shifts + emp2_shifts:
                sd = s["date"]
                if sd == day:
                    day_shifts.append(s)
            if day_shifts:
                schedule[day] = day_shifts

        result = validate_schedule(schedule)
        assert result.is_valid, f"Expected no violations but got: {[v.message for v in result.violations]}"
        assert len(result.violations) == 0


# ── test_violates_rest_time ─────────────────────────────────────────────────
class TestViolatesRestTime:
    def test_two_shifts_with_less_than_11h_gap(self):
        """Two shifts with <11h rest between them should be detected."""
        d = date(2025, 7, 1)
        shifts = [
            _shift(1, d, time(6, 0), d, time(22, 0)),
            _shift(1, d + timedelta(days=1), time(5, 0), d + timedelta(days=1), time(14, 0)),
        ]
        violations = validate_rest_time(shifts)
        assert len(violations) == 1
        assert violations[0].rule == "rest_time"
        assert "11h" in violations[0].message.lower() or "rest" in violations[0].message.lower()


# ── test_violates_max_daily_hours ───────────────────────────────────────────
class TestViolatesMaxDailyHours:
    def test_more_than_10h_in_a_day(self):
        """Shifts totaling >10h in a single day should be detected."""
        d = date(2025, 7, 1)
        shifts = [
            _shift(1, d, time(6, 0), d, time(16, 30), "11:00", "11:30"),  # 10h
        ]
        violations = validate_max_daily_hours(shifts)
        assert len(violations) == 1
        assert violations[0].rule == "max_daily_hours"


# ── test_violates_breaks ────────────────────────────────────────────────────
class TestViolatesBreaks:
    def test_shift_over_6h_without_break(self):
        """A single shift >6h without sufficient break should be detected."""
        d = date(2025, 7, 1)
        shifts = [
            _shift(1, d, time(6, 0), d, time(14, 0)),  # 8h, no break at all
        ]
        violations = validate_breaks(shifts)
        assert len(violations) == 1
        assert violations[0].rule == "breaks"

    def test_shift_over_9h_with_only_30min_break(self):
        """A shift >9h with only 30min break should be detected (needs 45min)."""
        d = date(2025, 7, 1)
        shifts = [
            _shift(1, d, time(6, 0), d, time(16, 0), "11:00", "11:30"),  # 10h, 30 min break
        ]
        violations = validate_breaks(shifts)
        assert len(violations) == 1
        assert violations[0].rule == "breaks"
        assert "45" in violations[0].message


# ── test_violates_consecutive_days ──────────────────────────────────────────
class TestViolatesConsecutiveDays:
    def test_more_than_6_consecutive_days(self):
        """Working 7+ consecutive days should be detected."""
        base = date(2025, 7, 1)
        shifts = [
            _shift(1, base + timedelta(days=i), time(8, 0), base + timedelta(days=i), time(16, 0)) for i in range(7)
        ]
        violations = validate_consecutive_days(shifts)
        assert len(violations) == 1
        assert violations[0].rule == "consecutive_days"


# ── test_overnight_shift_duration ───────────────────────────────────────────
class TestOvernightShiftDuration:
    def test_shift_crossing_midnight_calculated_correctly(self):
        """A shift from 22:00 to 06:00 is 8h and should be calculated correctly."""
        d = date(2025, 7, 1)
        shifts = [
            _shift(1, d, time(22, 0), d + timedelta(days=1), time(6, 0)),
        ]
        # No max_daily_hours violation: 8h
        violations = validate_max_daily_hours(shifts)
        assert len(violations) == 0

        # No break violation: <=6h (well, it's 8h but crosses days - break check is per-day)
        # Actually 8h work in a day (22:00-06:00 spans two calendar days but is one continuous shift)
        # The break validator should still detect missing break for >6h
        break_violations = validate_breaks(shifts)
        assert len(break_violations) == 1
        assert break_violations[0].rule == "breaks"
