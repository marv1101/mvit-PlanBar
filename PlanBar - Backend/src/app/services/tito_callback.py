import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, time, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models.employee import Contract, Employee, Timecard
from app.db.models.schedule import Schedule, Shiftplan
from app.schemas.tito import TiTOAssignment, TiTOCallbackPayload
from app.services.arbzg_cross_plan import collect_cross_plan_shifts, combine_weekly_history
from app.services.arbzg_rules import required_break_minutes
from app.services.arbzg_validator import ArbZgResult, validate_schedule
from app.services.holiday_service import get_german_holidays
from app.services.schedule_service import _get_week_type

logger = logging.getLogger(__name__)

# Status mapping (contract v2): only SUCCESS/FEASIBLE results are accepted as
# completed plans; TIMEOUT/INFEASIBLE/FAILED mark the schedule as failed and
# must never write shiftplans or timecards.
_COMPLETED_STATUSES = frozenset({"SUCCESS", "FEASIBLE", "COMPLETED"})  # COMPLETED = legacy alias
_FAILED_STATUSES = frozenset({"INFEASIBLE", "TIMEOUT", "FAILED"})
# Schedule statuses that mean "this terminal callback was already processed"
_ALREADY_PROCESSED = frozenset({"completed", "failed"})


class CallbackConflictError(Exception):
    """Raised when a callback cannot be processed for the schedule's current state.

    The endpoint maps this to HTTP 409 so TiTO stops retrying after its
    retry limit instead of looping forever.
    """

    def __init__(self, schedule_id: int, schedule_status: str):
        self.schedule_id = schedule_id
        self.schedule_status = schedule_status
        super().__init__(
            f"Callback für Schedule {schedule_id} im Status '{schedule_status}' nicht verarbeitbar "
            "(erwartet: 'submitted'; bereits verarbeitete Callbacks sind idempotent)"
        )


@dataclass
class _ParsedAssignment:
    """A successfully parsed, in-scope assignment ready to be written."""

    employee: Employee
    assignment: TiTOAssignment
    shift_date: date
    start_time: time
    end_time: time
    end_date: date  # differs from shift_date for overnight shifts
    break_start: str | None
    break_end: str | None
    break_minutes: int


def _extract_employee_id(value) -> int | None:
    """Robustly parse an employee id from a contract-v2 assignment.

    Accepts ints and the legacy string forms ("123", "emp_123").
    Returns None for unparseable values (caller records INVALID_ASSIGNMENT).
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.replace("emp_", "").strip())
        except ValueError:
            return None
    return None


def _parse_hhmm(value: str) -> time:
    """Parse "HH:MM" robustly; raises TypeError/ValueError for malformed values."""
    if not isinstance(value, str):
        raise TypeError(f"not a string: {value!r}")
    parts = value.split(":")
    if len(parts) < 2:
        raise ValueError(f"expected HH:MM, got {value!r}")
    hours, minutes = int(parts[0]), int(parts[1])
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        raise ValueError(f"time out of range: {value!r}")
    return time(hours, minutes)


def _format_hhmm(minutes: int) -> str:
    return f"{(minutes // 60) % 24:02d}:{minutes % 60:02d}"


def _normalize_break(
    start_t: time,
    end_t: time,
    employee: Employee,
    contract: Contract | None,
    assignment_break_minutes: int,
) -> tuple[str | None, str | None, int]:
    """Determine the break window written for a shift (A4).

    Policy:
    1. The employee's default break window (break_start/break_end) is used
       if it lies FULLY inside the shift window (overnight-aware).
    2. Otherwise a break of the effective duration is placed in the middle
       of the shift, with the start rounded to 15 minutes:
       duration = assignment.breakMinutes (solver view) or, if unset,
       the contract break time, or the statutory minimum (§ 4 ArbZG via
       app.services.arbzg_rules.required_break_minutes).
    3. A break duration of 0 minutes yields (None, None, 0) — no break
       written for shifts that need none.

    Returns (break_start, break_end, break_minutes).
    """
    start_m = start_t.hour * 60 + start_t.minute
    end_m = end_t.hour * 60 + end_t.minute
    if end_m <= start_m:
        end_m += 24 * 60
    duration_m = end_m - start_m

    # 1. Employee default window, if fully inside the shift window
    if employee.break_start and employee.break_end:
        try:
            bs = _parse_hhmm(employee.break_start)
            be = _parse_hhmm(employee.break_end)
        except ValueError:
            logger.warning(
                "Invalid employee break window %s-%s for employee %s",
                employee.break_start,
                employee.break_end,
                employee.id,
            )
        else:
            bs_m = bs.hour * 60 + bs.minute
            be_m = be.hour * 60 + be.minute
            if be_m <= bs_m:
                be_m += 24 * 60
            rel_bs = (bs_m - start_m) % (24 * 60)
            rel_be = rel_bs + (be_m - bs_m)
            if 0 < rel_be <= duration_m:
                return _format_hhmm(start_m + rel_bs), _format_hhmm(start_m + rel_be), be_m - bs_m

    # 2. Effective break duration, centered in the shift
    break_minutes = assignment_break_minutes or 0
    if break_minutes <= 0 and contract is not None:
        break_minutes = contract.break_time or 0
    if break_minutes <= 0:
        break_minutes = required_break_minutes(duration_m / 60.0)
    if break_minutes <= 0 or break_minutes >= duration_m:
        return None, None, 0

    rel_start = round((duration_m - break_minutes) / 2 / 15) * 15
    rel_start = max(0, min(rel_start, duration_m - break_minutes))
    return _format_hhmm(start_m + rel_start), _format_hhmm(start_m + rel_start + break_minutes), break_minutes


def _callback_violation(
    rule: str, message: str, employee_id: int | None = None, shift_date: date | None = None
) -> dict:
    """Payload-level violation (OUT_OF_SCOPE / INVALID_ASSIGNMENT) for diagnostics."""
    return {
        "rule": rule,
        "severity": "HARD" if rule == "INVALID_ASSIGNMENT" else "SOFT",
        "message": message,
        "employeeId": employee_id,
        "date": shift_date.isoformat() if shift_date else None,
    }


def _parse_assignments(
    db: Session,
    schedule: Schedule,
    assignments: list[TiTOAssignment],
) -> tuple[list[_ParsedAssignment], list[dict]]:
    """Parse assignments robustly (A4) and enforce the date scope (A1).

    - Unparseable employeeId/startTime/endTime or unknown employees skip the
      assignment and record an INVALID_ASSIGNMENT violation (no 500, no retry).
    - Assignments with a date outside [start_date, end_date] are discarded
      with an OUT_OF_SCOPE violation.
    """
    parsed: list[_ParsedAssignment] = []
    violations: list[dict] = []

    for a in assignments:
        shift_date = a.date if isinstance(a.date, date) else date.fromisoformat(str(a.date))

        emp_id = _extract_employee_id(a.employeeId)
        if emp_id is None:
            violations.append(
                _callback_violation(
                    "INVALID_ASSIGNMENT",
                    f"Mitarbeiter-ID '{a.employeeId}' konnte nicht gelesen werden — Assignment verworfen.",
                    shift_date=shift_date,
                )
            )
            continue

        employee = db.query(Employee).filter(Employee.id == emp_id).first()
        if employee is None:
            violations.append(
                _callback_violation(
                    "INVALID_ASSIGNMENT",
                    f"Unbekannter Mitarbeiter {emp_id} — Assignment verworfen.",
                    employee_id=emp_id,
                    shift_date=shift_date,
                )
            )
            continue

        try:
            start_t = _parse_hhmm(a.startTime)
            end_t = _parse_hhmm(a.endTime)
        except ValueError as exc:
            violations.append(
                _callback_violation(
                    "INVALID_ASSIGNMENT",
                    f"Ungültige Schichtzeiten für Mitarbeiter {emp_id} am {shift_date} "
                    f"({a.startTime!r}-{a.endTime!r}: {exc}) — Assignment verworfen.",
                    employee_id=emp_id,
                    shift_date=shift_date,
                )
            )
            continue

        # A1: date scope check — assignments outside the planning period are rejected
        if (
            schedule.start_date is not None
            and schedule.end_date is not None
            and not (schedule.start_date <= shift_date <= schedule.end_date)
        ):
            violations.append(
                _callback_violation(
                    "OUT_OF_SCOPE",
                    f"Assignment für Mitarbeiter {emp_id} am {shift_date} liegt außerhalb des "
                    f"Planungszeitraums ({schedule.start_date} bis {schedule.end_date}) — verworfen.",
                    employee_id=emp_id,
                    shift_date=shift_date,
                )
            )
            continue

        contract = employee.contracts[0] if employee.contracts else None
        break_start, break_end, break_minutes = _normalize_break(start_t, end_t, employee, contract, a.breakMinutes)
        end_date = shift_date + timedelta(days=1) if end_t <= start_t else shift_date

        parsed.append(
            _ParsedAssignment(
                employee=employee,
                assignment=a,
                shift_date=shift_date,
                start_time=start_t,
                end_time=end_t,
                end_date=end_date,
                break_start=break_start,
                break_end=break_end,
                break_minutes=break_minutes,
            )
        )

    return parsed, violations


def _arbzg_context(db: Session, parsed: list[_ParsedAssignment], schedule: Schedule) -> dict:
    """Build the keyword arguments for validate_schedule from parsed assignments."""
    employees = []
    seen: set[int] = set()
    for p in parsed:
        if p.employee.id in seen:
            continue
        seen.add(p.employee.id)
        employees.append(p.employee)

    holiday_dates: list[str] = []
    if schedule.start_date and schedule.end_date:
        holiday_dates = get_german_holidays(
            schedule.start_date,
            schedule.end_date,
            subdivision=settings.german_state,
        )

    weekly_history: dict[int, list[tuple[int, int, float]]] = {}
    if seen:
        timecards = db.query(Timecard).filter(Timecard.employee_id.in_(seen)).all()
        for tc in timecards:
            hours = tc.actual_hours if (tc.actual_hours or 0) > 0 else (tc.scheduled_hours or 0)
            weekly_history.setdefault(tc.employee_id, []).append((tc.year, tc.week, float(hours)))

    cross_plan_shifts = collect_cross_plan_shifts(db, schedule, seen)
    if schedule.start_date and cross_plan_shifts:
        weekly_history = combine_weekly_history(weekly_history, cross_plan_shifts, schedule.start_date)

    return {
        "employees": employees,
        "holidays": holiday_dates,
        "period_start": schedule.start_date,
        "period_end": schedule.end_date,
        "night_window_start": settings.night_window_start,
        "night_window_end": settings.night_window_end,
        "weekly_history": weekly_history,
        "planned_shifts": cross_plan_shifts,
    }


def process_tito_callback(db: Session, payload: TiTOCallbackPayload) -> Schedule | None:
    """Process a TiTO result/error callback (contract v2).

    Returns the schedule (200), None if no schedule matches the job_id (404),
    or raises CallbackConflictError (409) if the schedule's state does not
    allow processing.

    Guarantees:
    - SUCCESS/FEASIBLE: assignments are parsed robustly, scope-checked,
      ArbZG-validated (same rule set as the manual path) and written in a
      single transaction together with the result violations. HARD ArbZG
      violations reject the whole solution (status 'failed', existing draft
      shiftplans are kept); SOFT violations are persisted but accepted.
    - TIMEOUT/INFEASIBLE/FAILED: status 'failed', NO shiftplans/timecards
      are written; error/violations are persisted. The callback still
      returns the schedule (200) so TiTO does not retry forever.
    - Idempotency: a callback for an already processed schedule (completed
      or failed) is a no-op that still returns the schedule.
    """
    schedule = db.query(Schedule).filter(Schedule.tito_job_id == payload.job_id).with_for_update().first()
    if not schedule:
        return None

    # A3: state machine — only 'submitted' schedules accept new results.
    if schedule.status in _ALREADY_PROCESSED:
        # Terminal callback already processed (e.g. TiTO retry): idempotent no-op.
        logger.info(
            "Callback for job %s ignored: schedule %s already '%s'",
            payload.job_id,
            schedule.id,
            schedule.status,
        )
        return schedule
    if schedule.status != "submitted":
        raise CallbackConflictError(schedule.id, schedule.status)

    status = payload.status.upper()
    assignments = payload.assignments or (payload.solution.assignments if payload.solution else [])

    # Persist result metadata (merge to keep e.g. maximizeStaffing intact)
    metadata = dict(schedule.metadata_json or {})
    if payload.metadata is not None:
        metadata.update(payload.metadata.model_dump())
    else:
        metadata["callbackStatus"] = status
    schedule.metadata_json = metadata
    schedule.metrics_json = payload.metrics.model_dump() if payload.metrics else None

    diagnostics = payload.diagnostics.model_dump() if payload.diagnostics else {}
    aggregated = _aggregate_violations(schedule, payload)
    if aggregated:
        diagnostics["aggregatedMessages"] = aggregated
    raw_violations = payload.violations or (payload.metrics.violations if payload.metrics else None) or []
    if raw_violations:
        diagnostics["violations"] = raw_violations

    if status in _FAILED_STATUSES:
        # A2: failed result — no shiftplans/timecards, draft stays as working basis
        schedule.status = "failed"
        if payload.error:
            diagnostics["error"] = payload.error
        if payload.attempts is not None:
            diagnostics["attempts"] = payload.attempts
        schedule.diagnostics_json = diagnostics
        db.commit()
        db.refresh(schedule)
        return schedule

    # SUCCESS / FEASIBLE: parse + validate before writing anything (A1/A4)
    parsed, callback_violations = _parse_assignments(db, schedule, assignments)
    if callback_violations:
        diagnostics["callbackViolations"] = callback_violations

    arbzg_result: ArbZgResult | None = None
    if parsed:
        shift_dicts = [
            {
                "employee_id": p.employee.id,
                "date": p.shift_date,
                "start_time": p.start_time,
                "end_date": p.end_date,
                "end_time": p.end_time,
                "break_start": p.break_start,
                "break_end": p.break_end,
                "break_minutes": p.break_minutes,
            }
            for p in parsed
        ]
        arbzg_result = validate_schedule(shift_dicts, **_arbzg_context(db, parsed, schedule))
        diagnostics["arbZgViolations"] = [v.as_dict() for v in arbzg_result.violations]

    if arbzg_result is not None and arbzg_result.has_hard_violations:
        # A1: HARD ArbZG violations — do NOT blindly take over the result.
        schedule.status = "failed"
        schedule.diagnostics_json = diagnostics
        db.commit()
        db.refresh(schedule)
        logger.warning(
            "TiTO result for schedule %s rejected: %d HARD ArbZG violation(s)",
            schedule.id,
            len(arbzg_result.hard_violations),
        )
        return schedule

    # Accepted (possibly with SOFT violations): write shiftplans + status in ONE transaction
    schedule.status = "completed"
    schedule.diagnostics_json = diagnostics
    db.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).delete()
    for p in parsed:
        db.add(
            Shiftplan(
                schedule_id=schedule.id,
                employee_id=p.employee.id,
                date=p.shift_date,
                shift_id=p.assignment.shiftId,
                week=_get_week_type(p.shift_date),
                start_time=p.start_time,
                end_time=p.end_time,
                label=p.assignment.name or None,
                break_start=p.break_start,
                break_end=p.break_end,
            )
        )
    db.commit()
    db.refresh(schedule)
    db.expire(schedule, ["shiftplans"])

    if parsed:
        update_timecards_from_schedule(db, schedule)

    return schedule


def _parse_break_minutes(break_start: str | None, break_end: str | None) -> float:
    if break_start and break_end:
        try:
            start_parts = break_start.split(":")
            end_parts = break_end.split(":")
            start_mins = int(start_parts[0]) * 60 + int(start_parts[1])
            end_mins = int(end_parts[0]) * 60 + int(end_parts[1])
            return (end_mins - start_mins) / 60.0
        except (ValueError, IndexError):
            return 0.0
    return 0.0


def _calc_effective_hours(sp: Shiftplan, contract: Contract | None) -> float:
    """Net effective hours of a shift: attendance minus granted break.

    Break source order (shared rules per B1 — statutory defaults come from
    app.services.arbzg_rules, i.e. >6h→30min and >9h→45min):
    1. explicit break window on the shiftplan
    2. contract break time
    3. statutory minimum (§ 4 ArbZG via required_break_minutes)
    """
    start_mins = sp.start_time.hour * 60 + sp.start_time.minute
    end_mins = sp.end_time.hour * 60 + sp.end_time.minute
    duration = end_mins - start_mins
    if duration <= 0:
        duration += 24 * 60
    break_hours = _parse_break_minutes(sp.break_start, sp.break_end)
    if break_hours == 0.0 and contract:
        break_hours = contract.break_time / 60.0
    elif break_hours == 0.0:
        break_hours = required_break_minutes(duration / 60.0) / 60.0
    return max(0.0, duration / 60.0 - break_hours)


def update_timecards_from_schedule(db: Session, schedule: Schedule) -> None:
    """Create or update Timecards for all employees in a completed schedule.

    C4c: ``scheduled_hours`` per ISO week is computed ADDITIVELY across ALL
    schedules — the sum of every shiftplan of the employee in that week —
    instead of being overwritten by this schedule's shifts alone. The
    balance is recalculated from the recovered previous balance plus the
    new total delta, so overlapping schedules no longer lose each other's
    planned hours.
    """
    if not schedule.start_date or not schedule.end_date:
        logger.warning("Schedule %s has no date range, skipping timecard update", schedule.id)
        return

    db.expire(schedule, ["shiftplans"])
    own_shiftplans = db.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).all()
    if not own_shiftplans:
        return

    # Affected ISO weeks derive from this schedule's shifts; totals include
    # ALL shiftplans of the employees in those weeks (any schedule).
    affected_weeks: set[tuple[int, int]] = set()
    for sp in own_shiftplans:
        year, week, _ = sp.date.isocalendar()
        affected_weeks.add((year, week))

    weekly_data: dict[tuple[int, int], dict[int, float]] = defaultdict(lambda: defaultdict(float))
    weekly_emp_contracts: dict[int, Contract | None] = {}
    for year, week in affected_weeks:
        try:
            monday = date.fromisocalendar(year, week, 1)
        except ValueError:
            continue
        sunday = monday + timedelta(days=6)
        for sp in db.query(Shiftplan).filter(Shiftplan.date >= monday, Shiftplan.date <= sunday).all():
            contract = weekly_emp_contracts.get(sp.employee_id)
            if contract is None and sp.employee_id not in weekly_emp_contracts:
                contract = db.query(Contract).filter(Contract.employee_id == sp.employee_id).first()
                weekly_emp_contracts[sp.employee_id] = contract
            weekly_data[(year, week)][sp.employee_id] += _calc_effective_hours(sp, contract)

    employee_balance_cache: dict[int, float] = {}

    for year, week in sorted(weekly_data.keys(), key=lambda x: (x[0], x[1])):
        emp_hours = weekly_data[(year, week)]
        for emp_id, scheduled_hours in emp_hours.items():
            contract = weekly_emp_contracts.get(emp_id)
            contract_hours = float(contract.weekly_working_hours) if contract else 40.0

            existing = (
                db.query(Timecard)
                .filter(
                    Timecard.employee_id == emp_id,
                    Timecard.year == year,
                    Timecard.week == week,
                )
                .first()
            )

            if existing:
                is_adjustment = (
                    existing.scheduled_hours == 0.0
                    and existing.contract_hours == 0.0
                    and existing.manual_adjustment_hours != 0.0
                )

                if is_adjustment:
                    prev_balance = existing.balance
                else:
                    prev_balance = (
                        existing.balance
                        - (existing.scheduled_hours - existing.contract_hours)
                        - (existing.manual_adjustment_hours or 0)
                    )
            else:
                prev_balance = employee_balance_cache.get(emp_id)
                if prev_balance is None:
                    prev_tc = (
                        db.query(Timecard)
                        .filter(
                            Timecard.employee_id == emp_id,
                        )
                        .order_by(Timecard.year.desc(), Timecard.week.desc())
                        .first()
                    )
                    prev_balance = prev_tc.balance if prev_tc else 0.0

            delta = scheduled_hours - contract_hours
            new_balance = prev_balance + delta

            employee_balance_cache[emp_id] = new_balance

            if existing:
                existing.scheduled_hours = scheduled_hours
                existing.contract_hours = contract_hours
                existing.balance = new_balance
                if not is_adjustment:
                    existing.manual_adjustment_hours = 0.0
                    existing.adjustment_reason = None
            else:
                tc = Timecard(
                    employee_id=emp_id,
                    week=week,
                    year=year,
                    scheduled_hours=scheduled_hours,
                    contract_hours=contract_hours,
                    balance=new_balance,
                )
                db.add(tc)

    db.commit()


def _aggregate_violations(schedule: Schedule, payload: TiTOCallbackPayload) -> list[dict]:
    """Aggregate HARD unassigned-requirement violations by skill for the UI.

    Violations are read from the flat contract-v2 field first and fall back
    to the legacy metrics.violations shape.
    """
    violations = payload.violations or (payload.metrics.violations if payload.metrics else None) or []
    if not violations:
        return []

    shift_durations: dict[str, float] = {}
    if schedule.shift_templates:
        for st in schedule.shift_templates:
            start = st.get("startTime", "00:00")
            end = st.get("endTime", "00:00")
            try:
                start_h, start_m = map(int, start.split(":"))
                end_h, end_m = map(int, end.split(":"))
                duration = (end_h * 60 + end_m) - (start_h * 60 + start_m)
                if duration <= 0:
                    duration += 24 * 60
                shift_durations[st["id"]] = duration / 60.0
            except (ValueError, KeyError):
                continue

    by_skill: dict[str, dict] = defaultdict(lambda: {"count": 0, "hours": 0.0, "dates": set()})

    for violation in violations:
        if violation.get("severity") != "HARD":
            continue
        details = violation.get("details", {})
        skills = details.get("skills", [])
        skill = skills[0] if skills else "Unbekannt"
        shift_id = details.get("shiftTemplateId") or details.get("shiftId", "")
        cnt = details.get("count", 1)
        by_skill[skill]["count"] += cnt
        by_skill[skill]["hours"] += shift_durations.get(shift_id, 8.0) * cnt
        by_skill[skill]["dates"].add(details.get("date", ""))

    messages = []
    for skill, data in sorted(by_skill.items()):
        hours = round(data["hours"])
        if hours > 0:
            msg = (
                f"{hours} {skill}-Stunden konnten nicht besetzt werden "
                f"({data['count']} Schichten an {len(data['dates'])} Tagen)"
            )
        else:
            msg = f"{data['count']} {skill}-Schichten konnten nicht besetzt werden (an {len(data['dates'])} Tagen)"
        messages.append(
            {
                "severity": "HARD",
                "skill": skill,
                "message": msg,
                "totalMissingShifts": data["count"],
                "totalMissingHours": hours,
                "affectedDays": len(data["dates"]),
            }
        )

    return messages
