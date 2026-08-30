"""ArbZG (Arbeitszeitgesetz) compliance validator for manual shift planning.

Validates German labor law constraints when shifts are created manually
(not via TiTO which has its own constraint engine).

Key rules validated:
- §3: 11h minimum rest period between shifts
- §3: Maximum 10h daily working time
- §4: Break requirements (45min for >9h, 30min for >6h)
- §5: Maximum 6 consecutive working days
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# ── ArbZG constants ────────────────────────────────────────────────────────
MIN_REST_HOURS = 11  # §3 - minimum uninterrupted rest between shifts
MAX_DAILY_HOURS = 10  # §3 - maximum daily working time
BREAK_THRESHOLD_6H = 6  # §4 - break required after 6h
BREAK_MIN_30 = 30  # §4 - minimum 30 min break for >6h
BREAK_THRESHOLD_9H = 9  # §4 - extended break required after 9h
BREAK_MIN_45 = 45  # §4 - minimum 45 min break for >9h
MAX_CONSECUTIVE_DAYS = 6  # §5 - maximum consecutive working days


# ── Data structures ─────────────────────────────────────────────────────────
@dataclass
class ArbZgViolation:
    """A single ArbZG compliance violation."""

    rule: str
    message: str
    employee_id: int
    shift_date: date | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArbZgResult:
    """Result of an ArbZG compliance check."""

    is_valid: bool
    violations: list[ArbZgViolation] = field(default_factory=list)

    @property
    def warning_count(self) -> int:
        return len(self.violations)


# ── Internal helpers ────────────────────────────────────────────────────────
def _shift_start_datetime(shift: dict[str, Any]) -> datetime:
    """Return the full start datetime for a shift (date + start_time)."""
    d = shift["date"]
    st = shift["start_time"]
    if isinstance(d, str):
        d = date.fromisoformat(d)
    if isinstance(st, str):
        st = time.fromisoformat(st)
    return datetime.combine(d, st)


def _shift_end_datetime(shift: dict[str, Any]) -> datetime:
    """Return the full end datetime for a shift (handles overnight)."""
    sd = shift.get("date") or shift.get("start_date")
    ed = shift.get("end_date") or sd
    et = shift["end_time"]
    if isinstance(sd, str):
        sd = date.fromisoformat(sd)
    if isinstance(ed, str):
        ed = date.fromisoformat(ed)
    if isinstance(et, str):
        et = time.fromisoformat(et)
    return datetime.combine(ed, et)


def _shift_duration_hours(shift: dict[str, Any]) -> float:
    """Calculate shift duration in hours, correctly handling overnight shifts."""
    start = _shift_start_datetime(shift)
    end = _shift_end_datetime(shift)
    delta = end - start
    return delta.total_seconds() / 3600.0


def _get_break_minutes(shift: dict[str, Any]) -> int:
    """Calculate break duration in minutes from shift break_start/break_end."""
    bs = shift.get("break_start")
    be = shift.get("break_end")
    if not bs or not be:
        return 0
    if isinstance(bs, str):
        bs = time.fromisoformat(bs)
    if isinstance(be, str):
        be = time.fromisoformat(be)
    # Breaks are always within the same day as the shift start
    d = shift["date"] if isinstance(shift["date"], date) else date.fromisoformat(shift["date"])
    start_dt = datetime.combine(d, bs)
    end_dt = datetime.combine(d, be)
    # Handle midnight crossover for break (unlikely but safe)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    return int((end_dt - start_dt).total_seconds() / 60)


def _shifts_by_employee(shifts: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    """Group shifts by employee_id."""
    grouped: dict[int, list[dict[str, Any]]] = {}
    for s in shifts:
        eid = s["employee_id"]
        grouped.setdefault(eid, []).append(s)
    return grouped


def _shifts_by_date(shifts: list[dict[str, Any]]) -> dict[date, list[dict[str, Any]]]:
    """Group shifts by their start date."""
    grouped: dict[date, list[dict[str, Any]]] = {}
    for s in shifts:
        d = s["date"]
        if isinstance(d, str):
            d = date.fromisoformat(d)
        grouped.setdefault(d, []).append(s)
    return grouped


def _shifts_by_calendar_day(shifts: list[dict[str, Any]]) -> dict[date, list[dict[str, Any]]]:
    """Group shifts by calendar day they overlap with.

    An overnight shift from Mon 22:00 to Tue 06:00 is counted on both
    Mon and Tue for daily-hour aggregation (worst-case approach).
    """
    grouped: dict[date, list[dict[str, Any]]] = {}
    for s in shifts:
        sd = s["date"]
        if isinstance(sd, str):
            sd = date.fromisoformat(sd)
        ed = s.get("end_date") or sd
        if isinstance(ed, str):
            ed = date.fromisoformat(ed)
        # Add shift to every calendar day it spans
        current = sd
        while current <= ed:
            grouped.setdefault(current, []).append(s)
            current += timedelta(days=1)
    return grouped


# ── Public validation functions ─────────────────────────────────────────────
def validate_rest_time(shifts: list[dict[str, Any]]) -> list[ArbZgViolation]:
    """Check §3: minimum 11h rest between consecutive shifts for each employee.

    Shifts are sorted chronologically per employee. If the gap between
    the end of one shift and the start of the next is < 11 hours, a
    violation is raised for the *second* shift.
    """
    violations: list[ArbZgViolation] = []
    for eid, emp_shifts in _shifts_by_employee(shifts).items():
        sorted_shifts = sorted(emp_shifts, key=_shift_start_datetime)
        for i in range(1, len(sorted_shifts)):
            prev_end = _shift_end_datetime(sorted_shifts[i - 1])
            curr_start = _shift_start_datetime(sorted_shifts[i])
            gap = curr_start - prev_end
            gap_hours = gap.total_seconds() / 3600.0
            if gap_hours < MIN_REST_HOURS:
                sd = sorted_shifts[i].get("date")
                if isinstance(sd, str):
                    sd = date.fromisoformat(sd)
                violations.append(
                    ArbZgViolation(
                        rule="rest_time",
                        message=(
                            f"Insufficient rest time for employee {eid}: "
                            f"{gap_hours:.1f}h between shifts (minimum {MIN_REST_HOURS}h required). "
                            f"Previous shift ended {prev_end}, next starts {curr_start}."
                        ),
                        employee_id=eid,
                        shift_date=sd,
                        details={
                            "gap_hours": gap_hours,
                            "required_hours": MIN_REST_HOURS,
                            "prev_end": prev_end.isoformat(),
                            "next_start": curr_start.isoformat(),
                        },
                    )
                )
    return violations


def validate_max_daily_hours(shifts: list[dict[str, Any]]) -> list[ArbZgViolation]:
    """Check §3: maximum 10h daily working time per employee.

    For each calendar day, total working hours are computed.  Overnight
    shifts contribute hours to the days they span (split proportionally
    for a conservative worst-case estimate; here we use the full
    duration on the start date for simplicity and flag the start date).
    """
    violations: list[ArbZgViolation] = []
    for eid, emp_shifts in _shifts_by_employee(shifts).items():
        # Group shifts by their *original* start date for daily aggregation
        by_start_date = _shifts_by_date(emp_shifts)
        for d, day_shifts in by_start_date.items():
            total_hours = sum(_shift_duration_hours(s) for s in day_shifts)
            if total_hours > MAX_DAILY_HOURS:
                violations.append(
                    ArbZgViolation(
                        rule="max_daily_hours",
                        message=(
                            f"Employee {eid} exceeds {MAX_DAILY_HOURS}h maximum on {d}: {total_hours:.1f}h total."
                        ),
                        employee_id=eid,
                        shift_date=d,
                        details={
                            "total_hours": total_hours,
                            "max_hours": MAX_DAILY_HOURS,
                            "shift_count": len(day_shifts),
                        },
                    )
                )
    return violations


def validate_breaks(shifts: list[dict[str, Any]]) -> list[ArbZgViolation]:
    """Check §4: break requirements.

    - Shifts > 6h require at least 30 min break.
    - Shifts > 9h require at least 45 min break.
    - Breaks must be split into at least two periods for shifts > 6h
      (we check total break time; individual split is an additional
      refinement that can be added later).
    """
    violations: list[ArbZgViolation] = []
    for eid, emp_shifts in _shifts_by_employee(shifts).items():
        for s in emp_shifts:
            duration_h = _shift_duration_hours(s)
            break_min = _get_break_minutes(s)

            if duration_h <= BREAK_THRESHOLD_6H:
                continue  # No break required for ≤6h shifts

            if duration_h > BREAK_THRESHOLD_9H:
                required = BREAK_MIN_45
                label = f">{BREAK_THRESHOLD_9H}h"
            else:
                required = BREAK_MIN_30
                label = f">{BREAK_THRESHOLD_6H}h"

            if break_min < required:
                sd = s["date"]
                if isinstance(sd, str):
                    sd = date.fromisoformat(sd)
                violations.append(
                    ArbZgViolation(
                        rule="breaks",
                        message=(
                            f"Employee {eid} works {duration_h:.1f}h on {sd} ({label}) "
                            f"but has only {break_min}min break (minimum {required}min required)."
                        ),
                        employee_id=eid,
                        shift_date=sd,
                        details={
                            "duration_hours": duration_h,
                            "break_minutes": break_min,
                            "required_break_minutes": required,
                        },
                    )
                )
    return violations


def validate_consecutive_days(shifts: list[dict[str, Any]]) -> list[ArbZgViolation]:
    """Check §5: maximum 6 consecutive working days per employee.

    A working day is any day the employee has at least one shift.
    After 6 consecutive working days the 7th+ day is a violation.
    """
    violations: list[ArbZgViolation] = []
    for eid, emp_shifts in _shifts_by_employee(shifts).items():
        # Collect unique working dates
        working_dates: set[date] = set()
        for s in emp_shifts:
            d = s["date"]
            if isinstance(d, str):
                d = date.fromisoformat(d)
            working_dates.add(d)

        if not working_dates:
            continue

        sorted_dates = sorted(working_dates)
        streak = 1
        for i in range(1, len(sorted_dates)):
            if sorted_dates[i] - sorted_dates[i - 1] == timedelta(days=1):
                streak += 1
            else:
                streak = 1

            if streak > MAX_CONSECUTIVE_DAYS:
                violations.append(
                    ArbZgViolation(
                        rule="consecutive_days",
                        message=(
                            f"Employee {eid} works {streak} consecutive days "
                            f"(maximum {MAX_CONSECUTIVE_DAYS} allowed). "
                            f"Streak ends on {sorted_dates[i]}."
                        ),
                        employee_id=eid,
                        shift_date=sorted_dates[i],
                        details={
                            "consecutive_days": streak,
                            "max_days": MAX_CONSECUTIVE_DAYS,
                            "streak_end": sorted_dates[i].isoformat(),
                        },
                    )
                )
                # Only report once per streak
                streak = 0
    return violations


def validate_schedule(
    schedule_shifts: dict[date, list[dict[str, Any]]] | list[dict[str, Any]],
) -> ArbZgResult:
    """Run all ArbZG validations on a schedule.

    Accepts either:
      - A dict mapping dates to lists of shift dicts, or
      - A flat list of shift dicts (all shifts for all employees).

    Returns an ArbZgResult with all violations found.
    """
    # Normalize input: flatten to a single list of shift dicts
    all_shifts: list[dict[str, Any]] = []
    if isinstance(schedule_shifts, dict):
        for d, day_shifts in schedule_shifts.items():
            for s in day_shifts:
                # Ensure 'date' key is set
                s_copy = dict(s)
                if "date" not in s_copy:
                    s_copy["date"] = d
                all_shifts.append(s_copy)
    else:
        all_shifts = list(schedule_shifts)

    if not all_shifts:
        return ArbZgResult(is_valid=True, violations=[])

    violations: list[ArbZgViolation] = []
    violations.extend(validate_rest_time(all_shifts))
    violations.extend(validate_max_daily_hours(all_shifts))
    violations.extend(validate_breaks(all_shifts))
    violations.extend(validate_consecutive_days(all_shifts))

    is_valid = len(violations) == 0
    if not is_valid:
        logger.warning("ArbZG validation found %d violation(s)", len(violations))

    return ArbZgResult(is_valid=is_valid, violations=violations)
