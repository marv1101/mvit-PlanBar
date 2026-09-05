"""ArbZG / JArbSchG / MuSchG compliance validator for shift planning.

Used by BOTH planning paths (manual PUT and TiTO callback) so that TiTO
results and manual plans are validated against the same rule set.

Key rules (with correct legal references):
- § 3 ArbZG: maximum 10h daily working time — NET working time
  (attendance minus breaks; § 2 Abs. 1: Ruhepausen are not working time)
- § 3 S. 2 ArbZG: 48h average weekly working time (rolling, SOFT from history)
- § 4 ArbZG: breaks (30min for >6h up to 9h, 45min for >9h)
- § 5 ArbZG: 11h uninterrupted rest between shifts
- § 3 + § 9 ArbZG: maximum 6 consecutive working days
- § 9/§ 11 ArbZG: Sunday/holiday rest, >= 15 free Sundays per year (pro-rata SOFT)
- § 6 ArbZG: night work (10h net limit for night shifts, exam-date SOFT warning)
- § 11 Abs. 3 ArbZG: Ersatzruhetag after Sunday/holiday work (SOFT hint)
- JArbSchG (is_minor): 8h/day, 40h/week, 12h rest, no 20:00-06:00 work,
  no Saturday/Sunday/holiday work — HARD
- MuSchG (protection_until): no assignment during the protection period — HARD

Severity model:
- HARD violations must block acceptance (manual PUT -> 422, TiTO callback -> failed)
- SOFT violations are persisted/shown as warnings only
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from math import ceil
from typing import Any

from app.services.arbzg_rules import (
    BREAK_THRESHOLD_6H,
    BREAK_THRESHOLD_9H,
    ERSATZRUHETAG_HOLIDAY_DAYS,
    ERSATZRUHETAG_SUNDAY_DAYS,
    MAX_CONSECUTIVE_DAYS,
    MAX_DAILY_HOURS,
    MAX_WEEKLY_HOURS_LAW,
    MIN_FREE_SUNDAYS_PER_YEAR,
    MIN_REST_HOURS,
    MINOR_MAX_DAILY_HOURS,
    MINOR_MAX_WEEKLY_HOURS,
    MINOR_MIN_REST_HOURS,
    MINOR_NIGHT_REST_END,
    MINOR_NIGHT_REST_START,
    NIGHT_WINDOW_END,
    NIGHT_WINDOW_START,
    NIGHT_WORK_MAX_HOURS,
    SUNDAYS_PER_YEAR,
    required_break_minutes,
)

logger = logging.getLogger(__name__)

SEVERITY_HARD = "HARD"
SEVERITY_SOFT = "SOFT"

# Number of weeks considered for the rolling weekly average (§ 3 S. 2)
ROLLING_AVERAGE_WEEKS = 24


# ── Data structures ──────────────────────────────────────────────────────────
@dataclass
class ArbZgViolation:
    """A single ArbZG compliance violation."""

    rule: str
    message: str
    employee_id: int
    shift_date: date | None = None
    details: dict[str, Any] = field(default_factory=dict)
    severity: str = SEVERITY_HARD

    def as_dict(self) -> dict[str, Any]:
        """Serializable representation (persisted in diagnostics_json)."""
        return {
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
            "employeeId": self.employee_id,
            "date": self.shift_date.isoformat() if self.shift_date else None,
            "details": self.details,
        }


@dataclass
class ArbZgResult:
    """Result of an ArbZG compliance check."""

    is_valid: bool
    violations: list[ArbZgViolation] = field(default_factory=list)

    @property
    def warning_count(self) -> int:
        return len(self.violations)

    @property
    def hard_violations(self) -> list[ArbZgViolation]:
        return [v for v in self.violations if v.severity == SEVERITY_HARD]

    @property
    def soft_violations(self) -> list[ArbZgViolation]:
        return [v for v in self.violations if v.severity == SEVERITY_SOFT]

    @property
    def has_hard_violations(self) -> bool:
        return any(v.severity == SEVERITY_HARD for v in self.violations)


# ── Internal helpers ────────────────────────────────────────────────────────
def _to_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _to_time(value: Any) -> time:
    if isinstance(value, time):
        return value
    return time.fromisoformat(str(value))


def _shift_start_datetime(shift: dict[str, Any]) -> datetime:
    """Return the full start datetime for a shift (date + start_time)."""
    return datetime.combine(_to_date(shift["date"]), _to_time(shift["start_time"]))


def _shift_end_datetime(shift: dict[str, Any]) -> datetime:
    """Return the full end datetime for a shift (handles overnight).

    Uses ``end_date`` when present; if end_time <= start_time (overnight
    shift without explicit end_date), the end is assumed on the next day.
    """
    sd = _to_date(shift.get("date"))
    ed = _to_date(shift.get("end_date") or sd)
    end_dt = datetime.combine(ed, _to_time(shift["end_time"]))
    if end_dt <= _shift_start_datetime(shift):
        end_dt += timedelta(days=1)
    return end_dt


def _shift_duration_hours(shift: dict[str, Any]) -> float:
    """Gross attendance duration in hours (including breaks)."""
    delta = _shift_end_datetime(shift) - _shift_start_datetime(shift)
    return delta.total_seconds() / 3600.0


def _get_break_minutes(shift: dict[str, Any]) -> int:
    """Break duration in minutes.

    Prefers the explicit ``break_minutes`` key (callback path); falls back
    to computing the duration from break_start/break_end.
    """
    explicit = shift.get("break_minutes")
    if explicit is not None:
        try:
            return max(0, int(explicit))
        except (TypeError, ValueError):
            return 0
    bs = shift.get("break_start")
    be = shift.get("break_end")
    if not bs or not be:
        return 0
    d = _to_date(shift["date"])
    start_dt = datetime.combine(d, _to_time(bs))
    end_dt = datetime.combine(d, _to_time(be))
    # Handle midnight crossover for break (unlikely but safe)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    return int((end_dt - start_dt).total_seconds() / 60)


def _shift_net_hours(shift: dict[str, Any]) -> float:
    """Net working time in hours: attendance minus breaks (§ 2 Abs. 1 ArbZG)."""
    return max(0.0, _shift_duration_hours(shift) - _get_break_minutes(shift) / 60.0)


def _shifts_by_employee(shifts: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    """Group shifts by employee_id."""
    grouped: dict[int, list[dict[str, Any]]] = {}
    for s in shifts:
        grouped.setdefault(s["employee_id"], []).append(s)
    return grouped


def _shifts_by_date(shifts: list[dict[str, Any]]) -> dict[date, list[dict[str, Any]]]:
    """Group shifts by their start date."""
    grouped: dict[date, list[dict[str, Any]]] = {}
    for s in shifts:
        grouped.setdefault(_to_date(s["date"]), []).append(s)
    return grouped


def _covered_days(shift: dict[str, Any]) -> list[date]:
    """Calendar days a shift overlaps (start date through end date).

    Overnight shifts without an explicit end_date (end_time <= start_time)
    cover the following day as well.
    """
    sd = _to_date(shift["date"])
    ed = _to_date(shift.get("end_date") or sd)
    if ed == sd and _to_time(shift["end_time"]) <= _to_time(shift["start_time"]):
        ed = sd + timedelta(days=1)
    return [sd + timedelta(days=i) for i in range((ed - sd).days + 1)]


def _shift_overlaps_window(
    shift: dict[str, Any],
    window_start: time,
    window_end: time,
) -> bool:
    """True if the shift overlaps the daily window (e.g. night window 23:00-06:00)."""
    start_dt = _shift_start_datetime(shift)
    end_dt = _shift_end_datetime(shift)
    day = start_dt.date() - timedelta(days=1)
    last = end_dt.date()
    while day <= last:
        ws_dt = datetime.combine(day, window_start)
        we_dt = datetime.combine(day, window_end)
        if we_dt <= ws_dt:
            we_dt += timedelta(days=1)  # window crosses midnight
        if start_dt < we_dt and end_dt > ws_dt:
            return True
        day += timedelta(days=1)
    return False


def _employee_field(emp: Any, key: str, default: Any = None) -> Any:
    """Read a field from an employee dict OR an ORM-like object."""
    if isinstance(emp, dict):
        return emp.get(key, default)
    return getattr(emp, key, default)


def _employee_id(emp: Any) -> int:
    return int(_employee_field(emp, "id"))


def _employee_weekly_hours(emp: Any) -> float | None:
    """Contract weekly hours: dict key 'weekly_hours' or first ORM contract."""
    if isinstance(emp, dict):
        value = emp.get("weekly_hours")
        return float(value) if value is not None else None
    contracts = getattr(emp, "contracts", None) or []
    if contracts:
        return float(contracts[0].weekly_working_hours)
    return None


def _holiday_dates(holidays: list[date | str] | None) -> set[date]:
    if not holidays:
        return set()
    return {_to_date(h) for h in holidays}


def _period_bounds(
    shifts: list[dict[str, Any]],
    period_start: date | None,
    period_end: date | None,
) -> tuple[date | None, date | None]:
    """Resolve the planning period: explicit args win, else derived from shifts."""
    if period_start is not None and period_end is not None:
        return period_start, period_end
    if not shifts:
        return period_start, period_end
    dates = [_to_date(s["date"]) for s in shifts]
    return period_start or min(dates), period_end or max(dates)


def _sundays_in_period(period_start: date, period_end: date) -> list[date]:
    """All Sundays in [period_start, period_end]."""
    sundays = []
    current = period_start
    while current <= period_end:
        if current.weekday() == 6:
            sundays.append(current)
        current += timedelta(days=1)
    return sundays


# ── Public validation functions (4 core checks) ─────────────────────────────
def validate_rest_time(shifts: list[dict[str, Any]]) -> list[ArbZgViolation]:
    """Check § 5 ArbZG: minimum 11h rest between consecutive shifts for each employee.

    Shifts are sorted chronologically per employee. If the gap between
    the end of one shift and the start of the next is < 11 hours, a
    violation is raised for the *second* shift.
    """
    violations: list[ArbZgViolation] = []
    for eid, emp_shifts in _shifts_by_employee(shifts).items():
        sorted_shifts = sorted(emp_shifts, key=lambda s: _shift_start_datetime(s))
        for i in range(1, len(sorted_shifts)):
            prev_end = _shift_end_datetime(sorted_shifts[i - 1])
            curr_start = _shift_start_datetime(sorted_shifts[i])
            gap = curr_start - prev_end
            gap_hours = gap.total_seconds() / 3600.0
            if gap_hours < MIN_REST_HOURS:
                violations.append(
                    ArbZgViolation(
                        rule="rest_time",
                        message=(
                            f"Insufficient rest time (§ 5 ArbZG) for employee {eid}: "
                            f"{gap_hours:.1f}h between shifts (minimum {MIN_REST_HOURS}h required). "
                            f"Previous shift ended {prev_end}, next starts {curr_start}."
                        ),
                        employee_id=eid,
                        shift_date=_to_date(sorted_shifts[i].get("date")),
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
    """Check § 3 ArbZG: maximum 10h daily working time per employee (NET).

    Per § 2 Abs. 1 ArbZG, Ruhepausen do not count as working time: the
    check uses attendance duration minus granted breaks. Shifts are
    aggregated per calendar start date (worst-case flag on the start date).
    """
    violations: list[ArbZgViolation] = []
    for eid, emp_shifts in _shifts_by_employee(shifts).items():
        by_start_date = _shifts_by_date(emp_shifts)
        for d, day_shifts in by_start_date.items():
            total_hours = sum(_shift_net_hours(s) for s in day_shifts)
            if total_hours > MAX_DAILY_HOURS:
                violations.append(
                    ArbZgViolation(
                        rule="max_daily_hours",
                        message=(
                            f"Employee {eid} exceeds the {MAX_DAILY_HOURS}h daily maximum (§ 3 ArbZG) "
                            f"on {d}: {total_hours:.1f}h net working time."
                        ),
                        employee_id=eid,
                        shift_date=d,
                        details={
                            "total_hours": round(total_hours, 2),
                            "max_hours": MAX_DAILY_HOURS,
                            "shift_count": len(day_shifts),
                            "basis": "net",
                        },
                    )
                )
    return violations


def validate_breaks(shifts: list[dict[str, Any]]) -> list[ArbZgViolation]:
    """Check § 4 ArbZG: break requirements.

    - Shifts > 6h up to 9h require at least 30 min break.
    - Shifts > 9h require at least 45 min break.
    - Up to and including 6h: no statutory break required.
    Break thresholds come from app.services.arbzg_rules (single source).
    """
    violations: list[ArbZgViolation] = []
    for eid, emp_shifts in _shifts_by_employee(shifts).items():
        for s in emp_shifts:
            duration_h = _shift_duration_hours(s)
            break_min = _get_break_minutes(s)
            required = required_break_minutes(duration_h)
            if required == 0:
                continue

            if duration_h > BREAK_THRESHOLD_9H:
                label = f">{BREAK_THRESHOLD_9H}h"
            else:
                label = f">{BREAK_THRESHOLD_6H}h"

            if break_min < required:
                violations.append(
                    ArbZgViolation(
                        rule="breaks",
                        message=(
                            f"Employee {eid} works {duration_h:.1f}h on {_to_date(s['date'])} ({label}) "
                            f"but has only {break_min}min break (§ 4 ArbZG requires {required}min)."
                        ),
                        employee_id=eid,
                        shift_date=_to_date(s["date"]),
                        details={
                            "duration_hours": round(duration_h, 2),
                            "break_minutes": break_min,
                            "required_break_minutes": required,
                        },
                    )
                )
    return violations


def validate_consecutive_days(shifts: list[dict[str, Any]]) -> list[ArbZgViolation]:
    """Check § 3 + § 9 ArbZG: maximum 6 consecutive working days per employee.

    A working day is any day the employee has at least one shift.
    After 6 consecutive working days the 7th+ day is a violation.
    """
    violations: list[ArbZgViolation] = []
    for eid, emp_shifts in _shifts_by_employee(shifts).items():
        working_dates: set[date] = set()
        for s in emp_shifts:
            working_dates.update(_covered_days(s))

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
                            f"(maximum {MAX_CONSECUTIVE_DAYS} allowed, § 3 + § 9 ArbZG). "
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


# ── Extended validators (B4) ─────────────────────────────────────────────────
def validate_sunday_quota(
    shifts: list[dict[str, Any]],
    period_start: date | None,
    period_end: date | None,
) -> list[ArbZgViolation]:
    """§ 9/§ 11 ArbZG: at least 15 free Sundays per year (annual average rule).

    Enforced pro-rata per planning period as a SOFT warning: expected free
    Sundays = ceil(sundays_in_period * 15 / 52); the annual rule itself
    cannot be decided within a single schedule period.
    """
    if period_start is None or period_end is None:
        return []
    sundays = _sundays_in_period(period_start, period_end)
    if not sundays:
        return []
    expected_free = ceil(len(sundays) * MIN_FREE_SUNDAYS_PER_YEAR / SUNDAYS_PER_YEAR)
    allowed = max(0, len(sundays) - expected_free)

    violations: list[ArbZgViolation] = []
    for eid, emp_shifts in _shifts_by_employee(shifts).items():
        covered = set()
        for s in emp_shifts:
            covered.update(_covered_days(s))
        worked = sorted(d for d in sundays if d in covered)
        if len(worked) > allowed:
            violations.append(
                ArbZgViolation(
                    rule="sunday_quota",
                    severity=SEVERITY_SOFT,
                    message=(
                        f"Employee {eid} works {len(worked)} of {len(sundays)} Sundays in the period "
                        f"(§ 9/§ 11 ArbZG: at least {MIN_FREE_SUNDAYS_PER_YEAR} free Sundays per year, "
                        f"pro-rata {expected_free} of {len(sundays)} expected free)."
                    ),
                    employee_id=eid,
                    shift_date=worked[0],
                    details={
                        "worked_sundays": [d.isoformat() for d in worked],
                        "allowed": allowed,
                        "expected_free": expected_free,
                        "sundays_in_period": len(sundays),
                    },
                )
            )
    return violations


def validate_weekly_hours(
    shifts: list[dict[str, Any]],
    employees: list[Any] | None = None,
) -> list[ArbZgViolation]:
    """§ 3 S. 2 ArbZG: net weekly hours per ISO week <= min(contract hours, 48h).

    Exceeding the 48h legal limit is a HARD violation; exceeding the
    contract hours while staying under 48h is a SOFT warning (overtime is
    legally possible, but balance-relevant).
    """
    emp_index = {_employee_id(e): e for e in (employees or [])}
    weekly: dict[tuple[int, int], dict[int, float]] = {}
    for s in shifts:
        year, week, _ = _to_date(s["date"]).isocalendar()
        weekly.setdefault((year, week), {}).setdefault(s["employee_id"], 0.0)
        weekly[(year, week)][s["employee_id"]] += _shift_net_hours(s)

    violations: list[ArbZgViolation] = []
    for (year, week), emp_hours in sorted(weekly.items()):
        for eid, net_hours in emp_hours.items():
            contract = _employee_weekly_hours(emp_index.get(eid))
            if net_hours > MAX_WEEKLY_HOURS_LAW:
                violations.append(
                    ArbZgViolation(
                        rule="weekly_hours_law",
                        message=(
                            f"Employee {eid} exceeds the {MAX_WEEKLY_HOURS_LAW:g}h weekly maximum "
                            f"(§ 3 ArbZG) in ISO week {year}-W{week:02d}: {net_hours:.1f}h net."
                        ),
                        employee_id=eid,
                        details={
                            "year": year,
                            "week": week,
                            "net_hours": round(net_hours, 2),
                            "max_hours": MAX_WEEKLY_HOURS_LAW,
                        },
                    )
                )
            elif contract is not None and net_hours > contract:
                violations.append(
                    ArbZgViolation(
                        rule="weekly_hours_contract",
                        severity=SEVERITY_SOFT,
                        message=(
                            f"Employee {eid} exceeds the contracted {contract:g}h in ISO week "
                            f"{year}-W{week:02d}: {net_hours:.1f}h net (§ 48h legal limit not exceeded)."
                        ),
                        employee_id=eid,
                        details={
                            "year": year,
                            "week": week,
                            "net_hours": round(net_hours, 2),
                            "contract_hours": contract,
                        },
                    )
                )
    return violations


def validate_night_work(
    shifts: list[dict[str, Any]],
    employees: list[Any] | None = None,
    night_window_start: time | None = None,
    night_window_end: time | None = None,
) -> list[ArbZgViolation]:
    """§ 6 ArbZG: night work rules for night workers (is_night_worker=True).

    - Night shifts (overlap with the night window) must not exceed 10h net (HARD).
    - § 6 Abs. 1: a current Eignungsuntersuchung is required; a missing or
      outdated (> 1 year) night_worker_exam_date is a SOFT warning.
    """
    violations: list[ArbZgViolation] = []
    n_start = night_window_start or time.fromisoformat(NIGHT_WINDOW_START)
    n_end = night_window_end or time.fromisoformat(NIGHT_WINDOW_END)
    for emp in employees or []:
        eid = _employee_id(emp)
        emp_shifts = _shifts_by_employee(shifts).get(eid, [])
        night_shifts = [s for s in emp_shifts if _shift_overlaps_window(s, n_start, n_end)]
        if not night_shifts:
            continue

        for s in night_shifts:
            net = _shift_net_hours(s)
            if net > NIGHT_WORK_MAX_HOURS:
                violations.append(
                    ArbZgViolation(
                        rule="night_work_max_hours",
                        message=(
                            f"Night worker {eid} exceeds {NIGHT_WORK_MAX_HOURS:g}h net on a night shift "
                            f"(§ 6 ArbZG) on {_to_date(s['date'])}: {net:.1f}h."
                        ),
                        employee_id=eid,
                        shift_date=_to_date(s["date"]),
                        details={"net_hours": round(net, 2), "max_hours": NIGHT_WORK_MAX_HOURS},
                    )
                )

        exam = _employee_field(emp, "night_worker_exam_date")
        first_night = min(_to_date(s["date"]) for s in night_shifts)
        exam_date = _to_date(exam) if exam else None
        if exam_date is None or exam_date < first_night - timedelta(days=365):
            violations.append(
                ArbZgViolation(
                    rule="night_worker_exam",
                    severity=SEVERITY_SOFT,
                    message=(
                        f"Night worker {eid} has no current Eignungsuntersuchung (§ 6 Abs. 1 ArbZG): "
                        "night_worker_exam_date is missing or older than 1 year."
                    ),
                    employee_id=eid,
                    shift_date=first_night,
                    details={"exam_date": exam_date.isoformat() if exam_date else None},
                )
            )
    return violations


def validate_ersatzruhetag(
    shifts: list[dict[str, Any]],
    holidays: list[date | str] | None = None,
    period_end: date | None = None,
) -> list[ArbZgViolation]:
    """§ 11 Abs. 3 ArbZG: Ersatzruhetag after Sunday/holiday work (SOFT).

    After Sunday work a free day (24h) must follow within 2 calendar
    weeks; after work on a holiday that falls on a weekday, within 8
    weeks. The check is SOFT because the full calendar view (days beyond
    the planning period) is needed for a complete verification.
    """
    if period_end is None:
        return []
    holiday_dates = _holiday_dates(holidays)
    violations: list[ArbZgViolation] = []

    for eid, emp_shifts in _shifts_by_employee(shifts).items():
        covered = set()
        for s in emp_shifts:
            covered.update(_covered_days(s))

        demands: list[tuple[date, str, int]] = []  # (worked day, kind, deadline days)
        for d in sorted(covered):
            if d.weekday() == 6:
                demands.append((d, "sunday", ERSATZRUHETAG_SUNDAY_DAYS))
            elif d in holiday_dates:
                demands.append((d, "holiday", ERSATZRUHETAG_HOLIDAY_DAYS))

        for worked_day, kind, deadline_days in demands:
            deadline = worked_day + timedelta(days=deadline_days)
            search_end = min(deadline, period_end)
            has_free_day = any(d not in covered for d in range_date(worked_day + timedelta(days=1), search_end))
            if not has_free_day:
                verified = deadline <= period_end
                violations.append(
                    ArbZgViolation(
                        rule="ersatzruhetag",
                        severity=SEVERITY_SOFT,
                        message=(
                            f"Employee {eid} worked on {worked_day} ({kind}) — an Ersatzruhetag "
                            f"(free day, § 11 Abs. 3 ArbZG) is required by {deadline}."
                            + ("" if verified else " Could not be fully verified within the planning period.")
                        ),
                        employee_id=eid,
                        shift_date=worked_day,
                        details={
                            "kind": kind,
                            "deadline": deadline.isoformat(),
                            "verified": verified,
                        },
                    )
                )
    return violations


def range_date(start: date, end: date):
    """Yield dates in [start, end] (inclusive; empty if start > end)."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def validate_weekly_average(
    weekly_history: dict[int, list[tuple[int, int, float]]] | None,
    period_start: date | None,
) -> list[ArbZgViolation]:
    """§ 3 S. 2 ArbZG: rolling 24-week average of weekly hours <= 48h (SOFT).

    Uses the Timecards history (weeks strictly before the planning period).
    With less than 24 weeks of history, the average is computed over the
    available weeks; without any history the check is skipped.
    """
    if not weekly_history or period_start is None:
        return []
    period_key = period_start.isocalendar()[:2]
    violations: list[ArbZgViolation] = []
    for eid, weeks in weekly_history.items():
        past = sorted((y, w, h) for y, w, h in weeks if (y, w) < period_key)
        if not past:
            continue
        recent = past[-ROLLING_AVERAGE_WEEKS:]
        avg = sum(h for _, _, h in recent) / len(recent)
        if avg > MAX_WEEKLY_HOURS_LAW:
            violations.append(
                ArbZgViolation(
                    rule="weekly_average_hours",
                    severity=SEVERITY_SOFT,
                    message=(
                        f"Employee {eid} averages {avg:.1f}h/week over the last {len(recent)} weeks "
                        f"(§ 3 S. 2 ArbZG: max {MAX_WEEKLY_HOURS_LAW:g}h average)."
                    ),
                    employee_id=eid,
                    details={
                        "average_hours": round(avg, 2),
                        "weeks_considered": len(recent),
                        "max_hours": MAX_WEEKLY_HOURS_LAW,
                    },
                )
            )
    return violations


def validate_minor_rules(
    shifts: list[dict[str, Any]],
    employees: list[Any] | None = None,
    holidays: list[date | str] | None = None,
) -> list[ArbZgViolation]:
    """JArbSchG rules for minor employees (is_minor=True) — HARD violations.

    - max 8h net per day (§ 8)
    - max 40h net per week
    - 12h rest between shifts
    - no work during night rest 20:00-06:00 (§ 10)
    - no Sunday/holiday work (§ 9) and Saturday rest
    """
    violations: list[ArbZgViolation] = []
    minors = [e for e in (employees or []) if bool(_employee_field(e, "is_minor", False))]
    if not minors:
        return violations
    holiday_dates = _holiday_dates(holidays)
    night_start = time.fromisoformat(MINOR_NIGHT_REST_START)
    night_end = time.fromisoformat(MINOR_NIGHT_REST_END)

    for emp in minors:
        eid = _employee_id(emp)
        emp_shifts = _shifts_by_employee(shifts).get(eid, [])
        if not emp_shifts:
            continue

        # § 8: daily maximum
        for d, day_shifts in _shifts_by_date(emp_shifts).items():
            net = sum(_shift_net_hours(s) for s in day_shifts)
            if net > MINOR_MAX_DAILY_HOURS:
                violations.append(
                    ArbZgViolation(
                        rule="minor_daily_hours",
                        message=(
                            f"Minor employee {eid} exceeds {MINOR_MAX_DAILY_HOURS:g}h net on {d} "
                            f"(JArbSchG): {net:.1f}h."
                        ),
                        employee_id=eid,
                        shift_date=d,
                        details={"net_hours": round(net, 2), "max_hours": MINOR_MAX_DAILY_HOURS},
                    )
                )

        # weekly maximum
        weekly: dict[tuple[int, int], float] = {}
        for s in emp_shifts:
            year, week, _ = _to_date(s["date"]).isocalendar()
            weekly[(year, week)] = weekly.get((year, week), 0.0) + _shift_net_hours(s)
        for (year, week), net in sorted(weekly.items()):
            if net > MINOR_MAX_WEEKLY_HOURS:
                violations.append(
                    ArbZgViolation(
                        rule="minor_weekly_hours",
                        message=(
                            f"Minor employee {eid} exceeds {MINOR_MAX_WEEKLY_HOURS:g}h net in ISO week "
                            f"{year}-W{week:02d} (JArbSchG): {net:.1f}h."
                        ),
                        employee_id=eid,
                        details={"year": year, "week": week, "net_hours": round(net, 2)},
                    )
                )

        # rest time (12h)
        sorted_shifts = sorted(emp_shifts, key=lambda s: _shift_start_datetime(s))
        for i in range(1, len(sorted_shifts)):
            gap = _shift_start_datetime(sorted_shifts[i]) - _shift_end_datetime(sorted_shifts[i - 1])
            gap_hours = gap.total_seconds() / 3600.0
            if gap_hours < MINOR_MIN_REST_HOURS:
                violations.append(
                    ArbZgViolation(
                        rule="minor_rest_time",
                        message=(
                            f"Minor employee {eid} has only {gap_hours:.1f}h rest between shifts "
                            f"(JArbSchG requires {MINOR_MIN_REST_HOURS:g}h)."
                        ),
                        employee_id=eid,
                        shift_date=_to_date(sorted_shifts[i]["date"]),
                        details={"gap_hours": round(gap_hours, 2), "required_hours": MINOR_MIN_REST_HOURS},
                    )
                )

        # night rest 20:00-06:00
        night_dates = sorted(
            {_to_date(s["date"]) for s in emp_shifts if _shift_overlaps_window(s, night_start, night_end)}
        )
        if night_dates:
            violations.append(
                ArbZgViolation(
                    rule="minor_night_rest",
                    message=(
                        f"Minor employee {eid} works during the night rest "
                        f"{MINOR_NIGHT_REST_START}-{MINOR_NIGHT_REST_END} (JArbSchG): {night_dates[0]}."
                    ),
                    employee_id=eid,
                    shift_date=night_dates[0],
                    details={"dates": [d.isoformat() for d in night_dates]},
                )
            )

        # Sunday / Saturday / holiday work
        covered = set()
        for s in emp_shifts:
            covered.update(_covered_days(s))
        sundays = sorted(d for d in covered if d.weekday() == 6)
        if sundays:
            violations.append(
                ArbZgViolation(
                    rule="minor_sunday_work",
                    message=f"Minor employee {eid} works on a Sunday (JArbSchG § 9): {sundays[0]}.",
                    employee_id=eid,
                    shift_date=sundays[0],
                    details={"dates": [d.isoformat() for d in sundays]},
                )
            )
        holidays_worked = sorted(d for d in covered if d in holiday_dates)
        if holidays_worked:
            violations.append(
                ArbZgViolation(
                    rule="minor_holiday_work",
                    message=f"Minor employee {eid} works on a public holiday (JArbSchG § 9): {holidays_worked[0]}.",
                    employee_id=eid,
                    shift_date=holidays_worked[0],
                    details={"dates": [d.isoformat() for d in holidays_worked]},
                )
            )
        saturdays = sorted(d for d in covered if d.weekday() == 5)
        if saturdays:
            violations.append(
                ArbZgViolation(
                    rule="minor_saturday_rest",
                    message=f"Minor employee {eid} works on a Saturday (JArbSchG Samstagsruhe): {saturdays[0]}.",
                    employee_id=eid,
                    shift_date=saturdays[0],
                    details={"dates": [d.isoformat() for d in saturdays]},
                )
            )
    return violations


def validate_muschg(
    shifts: list[dict[str, Any]],
    employees: list[Any] | None = None,
) -> list[ArbZgViolation]:
    """MuSchG: employees with protection_until must not be scheduled up to that date (HARD)."""
    violations: list[ArbZgViolation] = []
    protected = {
        _employee_id(e): _to_date(_employee_field(e, "protection_until"))
        for e in (employees or [])
        if _employee_field(e, "protection_until")
    }
    if not protected:
        return violations
    for eid, emp_shifts in _shifts_by_employee(shifts).items():
        until = protected.get(eid)
        if until is None:
            continue
        affected = sorted(_to_date(s["date"]) for s in emp_shifts if _to_date(s["date"]) <= until)
        if affected:
            violations.append(
                ArbZgViolation(
                    rule="muschg_protection",
                    message=(f"Employee {eid} is protected until {until} (MuSchG) but is scheduled on {affected[0]}."),
                    employee_id=eid,
                    shift_date=affected[0],
                    details={"protection_until": until.isoformat(), "dates": [d.isoformat() for d in affected]},
                )
            )
    return violations


# ── Orchestration ────────────────────────────────────────────────────────────
def validate_schedule(
    schedule_shifts: dict[date, list[dict[str, Any]]] | list[dict[str, Any]],
    *,
    employees: list[Any] | None = None,
    holidays: list[date | str] | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
    night_window_start: str | None = None,
    night_window_end: str | None = None,
    weekly_history: dict[int, list[tuple[int, int, float]]] | None = None,
) -> ArbZgResult:
    """Run all ArbZG validations on a schedule (manual path AND TiTO callback path).

    Accepts either:
      - A dict mapping dates to lists of shift dicts, or
      - A flat list of shift dicts (all shifts for all employees).

    Optional keyword arguments extend the rule set beyond the 4 core checks:
      - employees: Employee ORM objects or dicts with id/weekly_hours/is_minor/
        is_night_worker/night_worker_exam_date/protection_until
      - holidays: holiday dates (date or ISO string) for § 9/§ 11 rules
      - period_start/period_end: planning period (derived from shifts if omitted)
      - night_window_start/night_window_end: § 6 night window ("HH:MM")
      - weekly_history: {employee_id: [(iso_year, iso_week, hours)]} from
        Timecards for the rolling 24-week average (§ 3 S. 2)

    Returns an ArbZgResult; use ``has_hard_violations`` to decide rejection.
    """
    # Normalize input: flatten to a single list of shift dicts
    all_shifts: list[dict[str, Any]] = []
    if isinstance(schedule_shifts, dict):
        for d, day_shifts in schedule_shifts.items():
            for s in day_shifts:
                s_copy = dict(s)
                if "date" not in s_copy:
                    s_copy["date"] = d
                all_shifts.append(s_copy)
    else:
        all_shifts = list(schedule_shifts)

    if not all_shifts:
        return ArbZgResult(is_valid=True, violations=[])

    p_start, p_end = _period_bounds(all_shifts, period_start, period_end)
    n_start = time.fromisoformat(night_window_start) if night_window_start else None
    n_end = time.fromisoformat(night_window_end) if night_window_end else None

    violations: list[ArbZgViolation] = []
    violations.extend(validate_rest_time(all_shifts))
    violations.extend(validate_max_daily_hours(all_shifts))
    violations.extend(validate_breaks(all_shifts))
    violations.extend(validate_consecutive_days(all_shifts))
    violations.extend(validate_weekly_hours(all_shifts, employees))
    violations.extend(validate_sunday_quota(all_shifts, p_start, p_end))
    violations.extend(validate_night_work(all_shifts, employees, n_start, n_end))
    violations.extend(validate_ersatzruhetag(all_shifts, holidays, p_end))
    violations.extend(validate_weekly_average(weekly_history, p_start))
    violations.extend(validate_minor_rules(all_shifts, employees, holidays))
    violations.extend(validate_muschg(all_shifts, employees))

    is_valid = len(violations) == 0
    if not is_valid:
        logger.warning(
            "ArbZG validation found %d violation(s) (%d HARD, %d SOFT)",
            len(violations),
            len([v for v in violations if v.severity == SEVERITY_HARD]),
            len([v for v in violations if v.severity == SEVERITY_SOFT]),
        )

    return ArbZgResult(is_valid=is_valid, violations=violations)
