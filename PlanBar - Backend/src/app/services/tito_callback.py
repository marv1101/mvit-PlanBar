import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.db.models.employee import Contract, Employee, Timecard
from app.db.models.schedule import Schedule, Shiftplan
from app.schemas.tito import TiTOCallbackPayload
from app.services.schedule_service import _get_week_type

logger = logging.getLogger(__name__)


def process_tito_callback(db: Session, payload: TiTOCallbackPayload) -> Schedule | None:
    schedule = db.query(Schedule).filter(Schedule.tito_job_id == payload.job_id).first()
    if not schedule:
        return None

    schedule.status = "completed" if payload.status.upper() in ("SUCCESS", "FEASIBLE", "COMPLETED") else "failed"
    schedule.metadata_json = payload.metadata.model_dump() if payload.metadata else None
    schedule.metrics_json = payload.metrics.model_dump() if payload.metrics else None
    schedule.diagnostics_json = payload.diagnostics.model_dump() if payload.diagnostics else None

    aggregated = _aggregate_violations(schedule, payload)
    if aggregated:
        diag = schedule.diagnostics_json or {}
        diag["aggregatedMessages"] = aggregated
        schedule.diagnostics_json = diag

    if payload.solution and payload.solution.assignments:
        db.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).delete()

        for assignment in payload.solution.assignments:
            employee = db.query(Employee).filter(
                Employee.id == _extract_employee_id(assignment.employeeId)
            ).first()

            if not employee:
                continue

            start_parts = assignment.startTime.split(":")
            end_parts = assignment.endTime.split(":")

            shiftplan = Shiftplan(
                schedule_id=schedule.id,
                employee_id=employee.id,
                date=assignment.date,
                shift_id=assignment.shiftId,
                week=_get_week_type(assignment.date),
                start_time=time(int(start_parts[0]), int(start_parts[1])),
                end_time=time(int(end_parts[0]), int(end_parts[1])),
                label=assignment.name or None,
                break_start=employee.break_start,
                break_end=employee.break_end,
            )
            db.add(shiftplan)

    db.commit()
    db.refresh(schedule)
    db.expire(schedule, ["shiftplans"])

    if payload.solution and payload.solution.assignments:
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
    start_mins = sp.start_time.hour * 60 + sp.start_time.minute
    end_mins = sp.end_time.hour * 60 + sp.end_time.minute
    duration = end_mins - start_mins
    if duration <= 0:
        duration += 24 * 60
    break_hours = _parse_break_minutes(sp.break_start, sp.break_end)
    if break_hours == 0.0 and contract:
        break_hours = contract.break_time / 60.0
    elif break_hours == 0.0:
        gesetzliche_pause = 0
        if duration >= 9 * 60:
            gesetzliche_pause = 45
        elif duration >= 6 * 60:
            gesetzliche_pause = 30
        break_hours = gesetzliche_pause / 60.0
    return max(0.0, duration / 60.0 - break_hours)


def update_timecards_from_schedule(db: Session, schedule: Schedule) -> None:
    """Create or update Timecards for all employees in a completed schedule."""
    if not schedule.start_date or not schedule.end_date:
        logger.warning("Schedule %s has no date range, skipping timecard update", schedule.id)
        return

    db.expire(schedule, ["shiftplans"])
    shiftplans = db.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).all()

    weekly_data: dict[tuple[int, int], dict[int, float]] = defaultdict(lambda: defaultdict(float))
    weekly_emp_contracts: dict[int, Contract | None] = {}

    for sp in shiftplans:
        year, week, _ = sp.date.isocalendar()
        contract = weekly_emp_contracts.get(sp.employee_id)
        if contract is None:
            contract = db.query(Contract).filter(Contract.employee_id == sp.employee_id).first()
            weekly_emp_contracts[sp.employee_id] = contract
        effective_hours = _calc_effective_hours(sp, contract)
        weekly_data[(year, week)][sp.employee_id] += effective_hours

    employee_balance_cache: dict[int, float] = {}

    for (year, week) in sorted(weekly_data.keys(), key=lambda x: (x[0], x[1])):
        emp_hours = weekly_data[(year, week)]
        for emp_id, scheduled_hours in emp_hours.items():
            contract = weekly_emp_contracts.get(emp_id)
            contract_hours = float(contract.weekly_working_hours) if contract else 40.0

            existing = db.query(Timecard).filter(
                Timecard.employee_id == emp_id,
                Timecard.year == year,
                Timecard.week == week,
            ).first()

            if existing:
                is_adjustment = (
                    existing.scheduled_hours == 0.0
                    and existing.contract_hours == 0.0
                    and existing.manual_adjustment_hours != 0.0
                )

                if is_adjustment:
                    prev_balance = existing.balance
                else:
                    prev_balance = existing.balance - (existing.scheduled_hours - existing.contract_hours) - (existing.manual_adjustment_hours or 0)
            else:
                prev_balance = employee_balance_cache.get(emp_id)
                if prev_balance is None:
                    prev_tc = db.query(Timecard).filter(
                        Timecard.employee_id == emp_id,
                    ).order_by(Timecard.year.desc(), Timecard.week.desc()).first()
                    prev_balance = prev_tc.balance if prev_tc else 0.0

            delta = scheduled_hours - contract_hours
            new_balance = prev_balance + delta

            employee_balance_cache[emp_id] = new_balance

            if existing:
                existing.scheduled_hours = scheduled_hours
                existing.contract_hours = contract_hours
                existing.balance = new_balance
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
    if not payload.metrics or not payload.metrics.violations:
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

    for violation in payload.metrics.violations:
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
        hours = int(round(data["hours"]))
        if hours > 0:
            msg = (
                f"{hours} {skill}-Stunden konnten nicht besetzt werden "
                f"({data['count']} Schichten an {len(data['dates'])} Tagen)"
            )
        else:
            msg = (
                f"{data['count']} {skill}-Schichten konnten nicht besetzt werden "
                f"(an {len(data['dates'])} Tagen)"
            )
        messages.append({
            "severity": "HARD",
            "skill": skill,
            "message": msg,
            "totalMissingShifts": data["count"],
            "totalMissingHours": hours,
            "affectedDays": len(data["dates"]),
        })

    return messages


def _extract_employee_id(employee_id_str: str) -> int:
    try:
        return int(employee_id_str.replace("emp_", ""))
    except (ValueError, AttributeError):
        logger.exception("Could not extract employee ID from '%s'", employee_id_str)
        return 0
