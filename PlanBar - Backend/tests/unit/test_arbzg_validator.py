"""Tests for ArbZG (Arbeitszeitgesetz) compliance validator."""

from datetime import date, time, timedelta

from app.services.arbzg_rules import MAX_DAILY_HOURS, required_break_minutes
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
    break_minutes: int | None = None,
) -> dict:
    """Helper to build a shift dict matching Shiftplan fields."""
    shift = {
        "employee_id": employee_id,
        "date": start_date,
        "start_time": start_time,
        "end_date": end_date,
        "end_time": end_time,
        "break_start": break_start,
        "break_end": break_end,
    }
    if break_minutes is not None:
        shift["break_minutes"] = break_minutes
    return shift


def _emp(
    emp_id: int = 1,
    weekly_hours: float | None = 40.0,
    is_minor: bool = False,
    is_night_worker: bool = False,
    night_worker_exam_date: date | None = None,
    protection_until: date | None = None,
) -> dict:
    """Employee data dict accepted by validate_schedule(..., employees=[...])."""
    return {
        "id": emp_id,
        "weekly_hours": weekly_hours,
        "is_minor": is_minor,
        "is_night_worker": is_night_worker,
        "night_worker_exam_date": night_worker_exam_date,
        "protection_until": protection_until,
    }


def _rules(result) -> set[tuple[str, str]]:
    return {(v.rule, v.severity) for v in result.violations}


# ── B1: shared break constants ──────────────────────────────────────────────
class TestSharedBreakRules:
    def test_required_break_minutes_boundaries(self):
        """§ 4 ArbZG: 'mehr als 6 bis zu 9 Stunden' → 30 min, 'mehr als 9' → 45 min."""
        assert required_break_minutes(6.0) == 0  # exactly 6h: no statutory break
        assert required_break_minutes(6.01) == 30
        assert required_break_minutes(9.0) == 30  # up to and including 9h
        assert required_break_minutes(9.01) == 45
        assert required_break_minutes(4.0) == 0


# ── test_valid_schedule_passes ──────────────────────────────────────────────
class TestValidSchedulePasses:
    def test_normal_schedule_no_violations(self):
        """A schedule with proper rest times and breaks should pass.

        Two employees each working up to 5 consecutive days, with at
        least 11h rest between shifts and proper breaks.
        """
        d = date(2025, 7, 1)
        emp1_shifts = [
            _shift(1, d + timedelta(days=i), time(8, 0), d + timedelta(days=i), time(16, 0), "12:00", "12:30")
            for i in range(5)
        ]
        emp2_shifts = [
            _shift(2, d + timedelta(days=i), time(6, 0), d + timedelta(days=i), time(13, 30), "10:00", "10:30")
            for i in range(5)
        ]

        schedule = {}
        for i in range(5):
            day = d + timedelta(days=i)
            day_shifts = [s for s in emp1_shifts + emp2_shifts if s["date"] == day]
            if day_shifts:
                schedule[day] = day_shifts

        result = validate_schedule(schedule)
        assert result.is_valid, f"Expected no violations but got: {[v.message for v in result.violations]}"
        assert len(result.violations) == 0

    def test_valid_schedule_with_employee_context(self):
        """Core checks pass with employee context supplied (no special rules triggered)."""
        d = date(2026, 6, 1)  # Monday
        shifts = [
            _shift(1, d + timedelta(days=i), time(8, 0), d + timedelta(days=i), time(16, 0), "12:00", "12:30")
            for i in range(5)  # Mon-Fri
        ]
        result = validate_schedule(
            shifts,
            employees=[_emp(1, weekly_hours=40.0)],
            holidays=["2026-06-04"],
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 7),
        )
        assert result.is_valid, [v.message for v in result.violations]


# ── Cross-plan validation (planned_shifts) ──────────────────────────────────
class TestCrossPlanValidation:
    """Rules evaluated across plan boundaries; attribution to the current plan."""

    D = date(2026, 6, 1)  # Monday, ISO week 23

    def test_rest_time_violation_across_plan_boundary(self):
        """Other plan ends 22:00, new plan starts 05:00 next day → HARD rest_time."""
        d = self.D
        other = [_shift(1, d, time(6, 0), d, time(22, 0))]
        current = [_shift(1, d + timedelta(days=1), time(5, 0), d + timedelta(days=1), time(14, 0))]
        result = validate_schedule(current, planned_shifts=other)
        rules = _rules(result)
        assert ("rest_time", "HARD") in rules

    def test_sufficient_rest_across_plan_boundary_passes(self):
        d = self.D
        other = [_shift(1, d, time(6, 0), d, time(22, 0))]
        current = [_shift(1, d + timedelta(days=1), time(9, 30), d + timedelta(days=1), time(14, 0))]
        result = validate_schedule(current, planned_shifts=other)
        assert result.is_valid, [v.message for v in result.violations]

    def test_rest_violation_inside_other_plan_only_not_flagged(self):
        """A violation fully contained in existing plans must not block the new plan."""
        d = self.D
        other = [
            _shift(1, d, time(6, 0), d, time(22, 0)),
            _shift(1, d + timedelta(days=1), time(5, 0), d + timedelta(days=1), time(14, 0)),
        ]
        current = [_shift(1, d + timedelta(days=5), time(8, 0), d + timedelta(days=5), time(16, 0), "12:00", "12:30")]
        result = validate_schedule(current, planned_shifts=other)
        assert result.is_valid, [v.message for v in result.violations]

    def test_consecutive_days_across_boundary(self):
        """Other plan: Sat+Sun; new plan: Mon..Thu → 6 days allowed... 7th flagged."""
        d = self.D  # Mon 2026-06-01 → Sat = d+5, Sun = d+6
        other = [
            _shift(1, d + timedelta(days=5), time(8, 0), d + timedelta(days=5), time(16, 0), "12:00", "12:30"),
            _shift(1, d + timedelta(days=6), time(8, 0), d + timedelta(days=6), time(16, 0), "12:00", "12:30"),
        ]
        six_days = [
            _shift(1, d + timedelta(days=7 + i), time(8, 0), d + timedelta(days=7 + i), time(16, 0), "12:00", "12:30")
            for i in range(4)
        ]
        result = validate_schedule(six_days, planned_shifts=other)
        assert result.is_valid, [v.message for v in result.violations]

        seven_days = [
            _shift(1, d + timedelta(days=7 + i), time(8, 0), d + timedelta(days=7 + i), time(16, 0), "12:00", "12:30")
            for i in range(5)
        ]
        result = validate_schedule(seven_days, planned_shifts=other)
        rules = _rules(result)
        assert ("consecutive_days", "HARD") in rules

    def test_consecutive_days_inside_other_plan_not_flagged(self):
        d = self.D
        other = [
            _shift(1, d + timedelta(days=5), time(6, 0), d + timedelta(days=5), time(22, 0)),
            _shift(1, d + timedelta(days=6), time(5, 0), d + timedelta(days=6), time(14, 0)),
            _shift(1, d + timedelta(days=7), time(5, 0), d + timedelta(days=7), time(14, 0)),
            _shift(1, d + timedelta(days=8), time(5, 0), d + timedelta(days=8), time(14, 0)),
            _shift(1, d + timedelta(days=9), time(5, 0), d + timedelta(days=9), time(14, 0)),
            _shift(1, d + timedelta(days=10), time(5, 0), d + timedelta(days=10), time(14, 0)),
            _shift(1, d + timedelta(days=11), time(5, 0), d + timedelta(days=11), time(14, 0)),
        ]
        current = [_shift(2, d, time(8, 0), d, time(16, 0), "12:00", "12:30")]
        result = validate_schedule(current, planned_shifts=other, employees=[_emp(1), _emp(2)])
        assert result.is_valid, [v.message for v in result.violations]

    def test_weekly_hours_exceeded_across_plans(self):
        """Other plan 50h + new plan 3h in same ISO week → weekly_hours_law (HARD)."""
        monday = date(2026, 6, 1)
        other = [
            _shift(1, monday + timedelta(days=i), time(7, 0), monday + timedelta(days=i), time(17, 0))
            for i in range(5)  # 5 × 10h = 50h
        ]
        current = [
            _shift(1, monday + timedelta(days=i), time(9, 0), monday + timedelta(days=i), time(12, 0))
            for i in range(5, 6)  # Sun? no — d+5 = Saturday 3h...
        ]
        result = validate_schedule(current, planned_shifts=other)
        rules = _rules(result)
        assert ("weekly_hours_law", "HARD") in rules

    def test_week_without_current_plan_shifts_not_flagged(self):
        """Other plan alone exceeds the weekly limit; new plan only in another week → ok."""
        d = self.D
        other = [
            _shift(1, d + timedelta(days=i), time(7, 0), d + timedelta(days=i), time(20, 0), "12:00", "12:45")
            for i in range(5)  # 5 × 13h = 65h
        ]
        next_monday = date(2026, 6, 8)
        current = [
            _shift(1, next_monday, time(8, 0), next_monday, time(16, 0), "12:00", "12:30"),
        ]
        result = validate_schedule(current, planned_shifts=other)
        assert result.is_valid, [v.message for v in result.violations]

    def test_unplanned_week_neutral(self):
        """Weeks with no planned shifts are assumed valid (no blocking)."""
        d = self.D
        current = [
            _shift(1, d, time(8, 0), d, time(16, 0), "12:00", "12:30"),
        ]
        result = validate_schedule(current, planned_shifts=[])
        assert result.is_valid, [v.message for v in result.violations]

    def test_same_day_reconstruction_only_current_aggregates_for_daily_hours(self):
        """Daily max uses current plan shifts only; cross shifts don't add up."""
        d = self.D
        other = [_shift(1, d, time(6, 0), d, time(13, 0))]  # 7h
        current = [_shift(1, d, time(13, 30), d, time(19, 0))]  # 5.5h (gap < 11h -> rest violation expected)
        result = validate_schedule(current, planned_shifts=other)
        rules = _rules(result)
        assert "max_daily_hours" not in [r for r, _ in rules]
        assert "rest_time" in [r for r, _ in rules]

    def test_attributed_rest_violation_when_other_shift_second(self):
        """New plan ends late; other plan starts early next day → also flagged."""
        d = self.D + timedelta(days=3)  # Thursday
        current = [_shift(1, d, time(12, 0), d, time(22, 0))]
        other = [_shift(1, d + timedelta(days=1), time(6, 0), d + timedelta(days=1), time(14, 0))]
        result = validate_schedule(current, planned_shifts=other)
        rules = _rules(result)
        assert ("rest_time", "HARD") in rules

    def test_behaviour_unchanged_without_planned_shifts(self):
        """No planned_shifts kwarg → classic per-schedule result."""
        d = self.D
        shifts = [
            _shift(1, d, time(6, 0), d, time(22, 0)),
            _shift(1, d + timedelta(days=1), time(5, 0), d + timedelta(days=1), time(14, 0)),
        ]
        violations = validate_rest_time(shifts)
        assert len(violations) == 1


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
        assert violations[0].severity == "HARD"

    def test_rest_time_message_references_paragraph_5(self):
        """B3: Ruhezeit is § 5 ArbZG (not § 3)."""
        d = date(2025, 7, 1)
        shifts = [
            _shift(1, d, time(6, 0), d, time(22, 0)),
            _shift(1, d + timedelta(days=1), time(5, 0), d + timedelta(days=1), time(14, 0)),
        ]
        violations = validate_rest_time(shifts)
        assert "§ 5" in violations[0].message


# ── test_violates_max_daily_hours (net time, B2) ────────────────────────────
class TestViolatesMaxDailyHours:
    def test_more_than_10h_net_in_a_day(self):
        """B2: § 2 Abs. 1 ArbZG — Ruhepausen do NOT count as working time.

        06:00-16:30 without a break = 10.5h net -> violation.
        """
        d = date(2025, 7, 1)
        shifts = [_shift(1, d, time(6, 0), d, time(16, 30))]  # 10.5h, no break
        violations = validate_max_daily_hours(shifts)
        assert len(violations) == 1
        assert violations[0].rule == "max_daily_hours"
        assert violations[0].details["total_hours"] > MAX_DAILY_HOURS
        assert "§ 3" in violations[0].message  # B3: daily max is § 3

    def test_10h_gross_with_30min_break_is_valid_net_time(self):
        """B2: 06:00-16:30 with 30 min break = 10.0h NET -> allowed.

        This is exactly the case the old brutto check wrongly flagged.
        """
        d = date(2025, 7, 1)
        shifts = [_shift(1, d, time(6, 0), d, time(16, 30), "11:00", "11:30")]
        violations = validate_max_daily_hours(shifts)
        assert violations == []

    def test_break_minutes_field_counts_as_net(self):
        """B2: explicit break_minutes (callback path) reduces net hours."""
        d = date(2025, 7, 1)
        shifts = [_shift(1, d, time(6, 0), d, time(16, 30), break_minutes=30)]
        assert validate_max_daily_hours(shifts) == []
        shifts = [_shift(1, d, time(6, 0), d, time(16, 30), break_minutes=0)]
        assert len(validate_max_daily_hours(shifts)) == 1

    def test_multiple_shifts_same_day_summed_net(self):
        """Two shifts on one day are summed (net) for the daily maximum."""
        d = date(2025, 7, 1)
        shifts = [
            _shift(1, d, time(6, 0), d, time(12, 30), "09:00", "09:30"),  # 6.0h net
            _shift(1, d, time(16, 30), d, time(21, 0), "18:00", "18:30"),  # 4.0h net
        ]
        assert validate_max_daily_hours(shifts) == []
        shifts[1] = _shift(1, d, time(16, 30), d, time(22, 0), "18:00", "18:30")  # 5.0h net -> 11h total
        assert len(validate_max_daily_hours(shifts)) == 1

    def test_manual_overnight_shift_end_after_start(self):
        """B2: end_time <= start_time without end_date is treated as next day."""
        d = date(2025, 7, 1)
        shifts = [_shift(1, d, time(22, 0), d, time(6, 0), "01:00", "01:30")]  # 7.5h net
        assert validate_max_daily_hours(shifts) == []


# ── test_violates_breaks ────────────────────────────────────────────────────
class TestViolatesBreaks:
    def test_shift_over_6h_without_break(self):
        """A single shift >6h without sufficient break should be detected."""
        d = date(2025, 7, 1)
        shifts = [_shift(1, d, time(6, 0), d, time(14, 0))]  # 8h, no break at all
        violations = validate_breaks(shifts)
        assert len(violations) == 1
        assert violations[0].rule == "breaks"
        assert "§ 4" in violations[0].message  # B3: breaks are § 4

    def test_shift_over_9h_with_only_30min_break(self):
        """A shift >9h with only 30min break should be detected (needs 45min)."""
        d = date(2025, 7, 1)
        shifts = [_shift(1, d, time(6, 0), d, time(16, 0), "11:00", "11:30")]  # 10h, 30 min break
        violations = validate_breaks(shifts)
        assert len(violations) == 1
        assert violations[0].rule == "breaks"
        assert "45" in violations[0].message

    def test_exactly_6h_needs_no_break(self):
        """B1: exactly 6h requires no statutory break ('mehr als 6 Stunden')."""
        d = date(2025, 7, 1)
        shifts = [_shift(1, d, time(8, 0), d, time(14, 0))]  # exactly 6h
        assert validate_breaks(shifts) == []

    def test_exactly_9h_30min_break_sufficient(self):
        """B1: exactly 9h falls into the 'more than 6 up to 9' bucket -> 30 min."""
        d = date(2025, 7, 1)
        shifts = [_shift(1, d, time(7, 0), d, time(16, 0), "11:00", "11:30")]  # 9h, 30 min
        assert validate_breaks(shifts) == []


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
        assert "§ 3" in violations[0].message and "§ 9" in violations[0].message  # B3


# ── test_overnight_shift_duration ───────────────────────────────────────────
class TestOvernightShiftDuration:
    def test_shift_crossing_midnight_calculated_correctly(self):
        """A shift from 22:00 to 06:00 is 8h and should be calculated correctly."""
        d = date(2025, 7, 1)
        shifts = [_shift(1, d, time(22, 0), d + timedelta(days=1), time(6, 0))]

        violations = validate_max_daily_hours(shifts)
        assert len(violations) == 0  # 8h net

        break_violations = validate_breaks(shifts)
        assert len(break_violations) == 1
        assert break_violations[0].rule == "breaks"


# ── B4a: Sunday quota (pro-rata, SOFT) ──────────────────────────────────────
class TestSundayQuota:
    def test_too_many_worked_sundays_is_soft_violation(self):
        """Pro-rata: 4 Sundays in period -> ceil(4*15/52)=2 must be free -> max. 2 worked."""
        # June 2026: Sundays are 07, 14, 21, 28
        worked_sundays = [date(2026, 6, 7), date(2026, 6, 14), date(2026, 6, 21)]  # 3 worked > 2 allowed
        shifts = []
        for i, sd in enumerate(worked_sundays):
            shifts.append(_shift(1, sd, time(8, 0), sd, time(16, 0), "12:00", "12:30"))
            # free days in between (no consecutive-day / ersatzruhetag issues)
            shifts.append(
                _shift(1, sd + timedelta(days=2), time(8, 0), sd + timedelta(days=2), time(16, 0), "12:00", "12:30")
            )
        result = validate_schedule(
            shifts,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 28),
        )
        assert ("sunday_quota", "SOFT") in _rules(result)
        assert not result.has_hard_violations

    def test_within_quota_is_ok(self):
        worked_sundays = [date(2026, 6, 7), date(2026, 6, 14)]  # 2 worked == 2 allowed
        shifts = []
        for sd in worked_sundays:
            shifts.append(_shift(1, sd, time(8, 0), sd, time(16, 0), "12:00", "12:30"))
            shifts.append(
                _shift(1, sd + timedelta(days=2), time(8, 0), sd + timedelta(days=2), time(16, 0), "12:00", "12:30")
            )
        result = validate_schedule(
            shifts,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 28),
        )
        assert ("sunday_quota", "SOFT") not in _rules(result)


# ── B4b: weekly hours ───────────────────────────────────────────────────────
class TestWeeklyHours:
    def test_over_48_law_limit_is_hard(self):
        """§ 3 S. 2 ArbZG: >48h net per ISO week is a HARD violation."""
        d = date(2026, 6, 1)  # Monday
        shifts = [
            _shift(1, d + timedelta(days=i), time(7, 0), d + timedelta(days=i), time(16, 30), "11:00", "11:30")
            for i in range(6)  # Mon-Sat, 8.5h net each -> 51h
        ]
        result = validate_schedule(shifts, employees=[_emp(1, weekly_hours=40.0)])
        assert ("weekly_hours_law", "HARD") in _rules(result)

    def test_over_contract_but_under_law_is_soft(self):
        """Contract hours exceeded (but <= 48h law limit) is a SOFT warning."""
        d = date(2026, 6, 1)
        shifts = [
            _shift(1, d + timedelta(days=i), time(8, 0), d + timedelta(days=i), time(16, 0), "12:00", "12:30")
            for i in range(6)  # 7.5h net * 6 = 45h > 20h contract, <= 48h law
        ]
        result = validate_schedule(shifts, employees=[_emp(1, weekly_hours=20.0)])
        assert ("weekly_hours_contract", "SOFT") in _rules(result)
        assert ("weekly_hours_law", "HARD") not in _rules(result)
        assert not result.has_hard_violations

    def test_within_limits_ok(self):
        d = date(2026, 6, 1)
        shifts = [
            _shift(1, d + timedelta(days=i), time(8, 0), d + timedelta(days=i), time(16, 0), "12:00", "12:30")
            for i in range(5)  # 7.5h * 5 = 37.5h
        ]
        result = validate_schedule(shifts, employees=[_emp(1, weekly_hours=40.0)])
        assert "weekly_hours_law" not in {r for r, _ in _rules(result)}
        assert "weekly_hours_contract" not in {r for r, _ in _rules(result)}


# ── B4c: night work § 6 ─────────────────────────────────────────────────────
class TestNightWork:
    def test_night_shift_over_10h_net_is_hard(self):
        """§ 6: night workers must not exceed 10h net on night shifts."""
        d = date(2026, 6, 1)
        shifts = [_shift(1, d, time(19, 0), d + timedelta(days=1), time(6, 30), "01:00", "01:45")]  # 10.75h net
        result = validate_schedule(
            shifts,
            employees=[_emp(1, is_night_worker=True, night_worker_exam_date=date(2026, 5, 1))],
        )
        assert ("night_work_max_hours", "HARD") in _rules(result)

    def test_missing_exam_date_is_soft_warning(self):
        d = date(2026, 6, 1)
        shifts = [_shift(1, d, time(22, 0), d + timedelta(days=1), time(6, 0), "01:00", "01:30")]  # 7.5h net
        result = validate_schedule(shifts, employees=[_emp(1, is_night_worker=True)])
        assert ("night_worker_exam", "SOFT") in _rules(result)
        assert not result.has_hard_violations

    def test_outdated_exam_date_is_soft_warning(self):
        d = date(2026, 6, 1)
        shifts = [_shift(1, d, time(22, 0), d + timedelta(days=1), time(6, 0), "01:00", "01:30")]
        result = validate_schedule(
            shifts,
            employees=[_emp(1, is_night_worker=True, night_worker_exam_date=date(2024, 6, 1))],  # > 1 year old
        )
        assert ("night_worker_exam", "SOFT") in _rules(result)

    def test_recent_exam_date_no_warning(self):
        d = date(2026, 6, 1)
        shifts = [_shift(1, d, time(22, 0), d + timedelta(days=1), time(6, 0), "01:00", "01:30")]
        result = validate_schedule(
            shifts,
            employees=[_emp(1, is_night_worker=True, night_worker_exam_date=date(2026, 1, 1))],
        )
        assert ("night_worker_exam", "SOFT") not in _rules(result)

    def test_day_shift_no_night_rules(self):
        """Shift outside the night window does not trigger night worker rules."""
        d = date(2026, 6, 1)
        shifts = [_shift(1, d, time(8, 0), d, time(16, 0), "12:00", "12:30")]
        result = validate_schedule(shifts, employees=[_emp(1, is_night_worker=True)])
        assert "night_worker_exam" not in {r for r, _ in _rules(result)}


# ── B4d: Ersatzruhetag § 11 Abs. 3 (SOFT) ───────────────────────────────────
class TestErsatzruhetag:
    def test_sunday_work_without_free_day_is_soft(self):
        """After Sunday work a free day must follow within 2 calendar weeks."""
        sunday = date(2026, 6, 7)
        shifts = [
            _shift(1, sunday + timedelta(days=i), time(8, 0), sunday + timedelta(days=i), time(16, 0), "12:00", "12:30")
            for i in range(3)  # works 07.-09.06, no free day up to period end
        ]
        result = validate_schedule(
            shifts,
            period_start=date(2026, 6, 7),
            period_end=date(2026, 6, 9),
        )
        assert ("ersatzruhetag", "SOFT") in _rules(result)
        assert not result.has_hard_violations

    def test_sunday_work_with_free_day_ok(self):
        sunday = date(2026, 6, 7)
        shifts = [
            _shift(1, sunday, time(8, 0), sunday, time(16, 0), "12:00", "12:30"),
            _shift(
                1, sunday + timedelta(days=1), time(8, 0), sunday + timedelta(days=1), time(16, 0), "12:00", "12:30"
            ),
            # 09.-13.06 free, then Sat 13.06? -> 08+09 worked, 10-13 free
        ]
        result = validate_schedule(
            shifts,
            period_start=date(2026, 6, 7),
            period_end=date(2026, 6, 14),
        )
        assert ("ersatzruhetag", "SOFT") not in _rules(result)

    def test_holiday_work_without_free_day_is_soft(self):
        """Holiday work (holiday on a weekday) requires a free day within 8 weeks."""
        holiday = date(2026, 6, 4)  # Thursday (e.g. Fronleichnam in BW)
        shifts = [
            _shift(
                1, holiday + timedelta(days=i), time(8, 0), holiday + timedelta(days=i), time(16, 0), "12:00", "12:30"
            )
            for i in range(3)  # works 04.-06.06, no free day up to period end
        ]
        result = validate_schedule(
            shifts,
            holidays=["2026-06-04"],
            period_start=date(2026, 6, 4),
            period_end=date(2026, 6, 6),
        )
        assert ("ersatzruhetag", "SOFT") in _rules(result)
        violations = [v for v in result.violations if v.rule == "ersatzruhetag"]
        assert violations[0].details["kind"] == "holiday"


# ── B4e: rolling 24-week average (SOFT) ─────────────────────────────────────
class TestRollingAverage:
    def test_history_average_over_48h_is_soft_warning(self):
        d = date(2026, 6, 1)
        shifts = [_shift(1, d, time(8, 0), d, time(16, 0), "12:00", "12:30")]
        history = {1: [(2026, wk, 50.0) for wk in range(1, 25)]}  # 24 weeks a 50h
        result = validate_schedule(
            shifts,
            weekly_history=history,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 7),
        )
        assert ("weekly_average_hours", "SOFT") in _rules(result)
        assert not result.has_hard_violations

    def test_short_history_uses_available_weeks(self):
        """< 24 weeks of history: average over the available weeks."""
        d = date(2026, 6, 1)
        shifts = [_shift(1, d, time(8, 0), d, time(16, 0), "12:00", "12:30")]
        history = {1: [(2026, 21, 50.0), (2026, 22, 50.0)]}  # only 2 weeks
        result = validate_schedule(
            shifts,
            weekly_history=history,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 7),
        )
        assert ("weekly_average_hours", "SOFT") in _rules(result)

    def test_history_under_48h_no_warning(self):
        d = date(2026, 6, 1)
        shifts = [_shift(1, d, time(8, 0), d, time(16, 0), "12:00", "12:30")]
        history = {1: [(2026, wk, 40.0) for wk in range(1, 25)]}
        result = validate_schedule(
            shifts,
            weekly_history=history,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 7),
        )
        assert ("weekly_average_hours", "SOFT") not in _rules(result)

    def test_no_history_no_warning(self):
        d = date(2026, 6, 1)
        shifts = [_shift(1, d, time(8, 0), d, time(16, 0), "12:00", "12:30")]
        result = validate_schedule(
            shifts,
            weekly_history={},
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 7),
        )
        assert "weekly_average_hours" not in {r for r, _ in _rules(result)}


# ── B4f: JArbSchG minors (HARD) ─────────────────────────────────────────────
class TestMinorRules:
    def test_minor_over_8h_daily(self):
        d = date(2026, 6, 3)
        shifts = [_shift(1, d, time(8, 0), d, time(17, 0), "12:00", "12:30")]  # 8.5h net
        result = validate_schedule(shifts, employees=[_emp(1, is_minor=True)])
        assert ("minor_daily_hours", "HARD") in _rules(result)

    def test_minor_over_40h_weekly(self):
        d = date(2026, 6, 1)
        shifts = [
            _shift(1, d + timedelta(days=i), time(8, 0), d + timedelta(days=i), time(15, 30), "11:00", "11:30")
            for i in range(6)  # 6.5h net * 6 = 39h ... need >40: 7h net * 6 = 42
        ]
        shifts = [
            _shift(1, d + timedelta(days=i), time(8, 0), d + timedelta(days=i), time(16, 0), "11:00", "11:30")
            for i in range(6)  # 7.0h net * 6 = 42h > 40h
        ]
        result = validate_schedule(shifts, employees=[_emp(1, is_minor=True)])
        assert ("minor_weekly_hours", "HARD") in _rules(result)

    def test_minor_less_than_12h_rest(self):
        d = date(2026, 6, 3)
        shifts = [
            _shift(1, d, time(8, 0), d, time(16, 0), "12:00", "12:30"),
            _shift(
                1, d + timedelta(days=1), time(3, 0), d + timedelta(days=1), time(11, 0), "07:00", "07:30"
            ),  # 11h gap
        ]
        result = validate_schedule(shifts, employees=[_emp(1, is_minor=True)])
        assert ("minor_rest_time", "HARD") in _rules(result)
        # 11h gap is fine for adults (§ 5: 11h) -> no adult rest_time violation
        assert "rest_time" not in {r for r, _ in _rules(result)}

    def test_minor_night_rest_20_to_06(self):
        d = date(2026, 6, 3)
        shifts = [_shift(1, d, time(19, 0), d + timedelta(days=1), time(3, 0), "22:00", "22:30")]
        result = validate_schedule(shifts, employees=[_emp(1, is_minor=True)])
        assert ("minor_night_rest", "HARD") in _rules(result)

    def test_minor_sunday_work(self):
        sunday = date(2026, 6, 7)
        shifts = [_shift(1, sunday, time(8, 0), sunday, time(14, 0))]  # 6h, no break needed
        result = validate_schedule(
            shifts,
            employees=[_emp(1, is_minor=True)],
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 7),
        )
        assert ("minor_sunday_work", "HARD") in _rules(result)

    def test_minor_holiday_work(self):
        holiday = date(2026, 6, 4)  # Thursday
        shifts = [_shift(1, holiday, time(8, 0), holiday, time(14, 0))]
        result = validate_schedule(
            shifts,
            employees=[_emp(1, is_minor=True)],
            holidays=["2026-06-04"],
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 7),
        )
        assert ("minor_holiday_work", "HARD") in _rules(result)

    def test_minor_saturday_work(self):
        saturday = date(2026, 6, 6)
        shifts = [_shift(1, saturday, time(8, 0), saturday, time(14, 0))]
        result = validate_schedule(
            shifts,
            employees=[_emp(1, is_minor=True)],
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 7),
        )
        assert ("minor_saturday_rest", "HARD") in _rules(result)

    def test_minor_within_limits_ok(self):
        d = date(2026, 6, 1)
        shifts = [
            _shift(1, d + timedelta(days=i), time(8, 0), d + timedelta(days=i), time(14, 0))  # 6h net
            for i in range(5)  # Mon-Fri, 30h/week
        ]
        result = validate_schedule(
            shifts,
            employees=[_emp(1, is_minor=True)],
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 7),
        )
        assert not result.has_hard_violations, [v.message for v in result.violations]


# ── B4g: MuSchG protection (HARD) ───────────────────────────────────────────
class TestMuSchGProtection:
    def test_assignment_within_protection_period_is_hard(self):
        d = date(2026, 6, 3)
        shifts = [_shift(1, d, time(8, 0), d, time(16, 0), "12:00", "12:30")]
        result = validate_schedule(shifts, employees=[_emp(1, protection_until=date(2026, 6, 10))])
        assert ("muschg_protection", "HARD") in _rules(result)

    def test_assignment_after_protection_period_ok(self):
        d = date(2026, 6, 20)
        shifts = [_shift(1, d, time(8, 0), d, time(16, 0), "12:00", "12:30")]
        result = validate_schedule(shifts, employees=[_emp(1, protection_until=date(2026, 6, 10))])
        assert "muschg_protection" not in {r for r, _ in _rules(result)}


# ── severity classification ─────────────────────────────────────────────────
class TestSeverityClassification:
    def test_hard_and_soft_violation_properties(self):
        d = date(2026, 6, 7)  # Sunday
        shifts = [
            _shift(1, d, time(6, 0), d, time(19, 0))
        ]  # 13h no break: HARD daily + HARD breaks + SOFT sunday/ersatz
        result = validate_schedule(
            shifts,
            employees=[_emp(1)],
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 7),
        )
        assert result.has_hard_violations
        assert all(v.severity == "HARD" for v in result.hard_violations)
        assert all(v.severity == "SOFT" for v in result.soft_violations)
        assert not result.is_valid

    def test_only_soft_violations_is_valid_for_hard_gate(self):
        d = date(2026, 6, 7)  # Sunday
        shifts = [_shift(1, d, time(8, 0), d, time(16, 0), "12:00", "12:30")]
        result = validate_schedule(
            shifts,
            employees=[_emp(1)],
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 7),
        )
        assert not result.has_hard_violations
        assert len(result.soft_violations) > 0  # sunday work -> SOFT warnings
        assert not result.is_valid  # violations exist (soft)
