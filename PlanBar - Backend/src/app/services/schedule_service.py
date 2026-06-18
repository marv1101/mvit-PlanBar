import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models.employee import Employee, Timecard
from app.db.models.role import Role
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.shift_wish import ShiftWish
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ShiftplanCreate
from app.services import audit_service
from app.services.arbzg_validator import ArbZgResult, validate_schedule
from app.services.tito_proxy import tito_proxy

logger = logging.getLogger(__name__)


def create_schedule(db: Session, data: ScheduleCreate, user_id: int | None = None) -> Schedule:
    schedule = Schedule(
        name=data.name,
        week_type=data.week_type,
        start_date=data.start_date,
        end_date=data.end_date,
        role_requirements=data.role_requirements,
        shift_templates=data.shift_templates,
        status="draft",
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    for shiftplan_data in data.shiftplans:
        shiftplan = Shiftplan(
            schedule_id=schedule.id,
            employee_id=shiftplan_data.employee_id,
            date=shiftplan_data.date,
            shift_id=shiftplan_data.shift_id,
            start_time=shiftplan_data.start_time,
            end_time=shiftplan_data.end_time,
            week=shiftplan_data.week,
            break_start=shiftplan_data.break_start,
            break_end=shiftplan_data.break_end,
            label=shiftplan_data.label,
            notes=shiftplan_data.notes,
        )
        db.add(shiftplan)

    db.commit()
    db.refresh(schedule)
    audit_service.log_create(db, user_id=user_id, resource_type="schedule", resource_id=str(schedule.id))
    return schedule


def get_schedule_by_id(db: Session, schedule_id: int) -> Schedule | None:
    return db.query(Schedule).filter(Schedule.id == schedule_id).first()


def list_schedules(db: Session) -> list[Schedule]:
    return db.query(Schedule).order_by(Schedule.created_at.desc()).all()


def update_schedule(db: Session, schedule: Schedule, data: ScheduleUpdate, actor_id: int | None = None) -> Schedule:
    if data.name is not None:
        schedule.name = data.name
    if data.week_type is not None:
        schedule.week_type = data.week_type
    if data.status is not None:
        schedule.status = data.status.value
    if data.shift_templates is not None:
        schedule.shift_templates = data.shift_templates
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    audit_service.log_update(db, user_id=actor_id, resource_type="schedule", resource_id=str(schedule.id))
    return schedule


def delete_schedule(db: Session, schedule: Schedule, actor_id: int | None = None) -> None:
    db.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).delete()
    db.delete(schedule)
    db.commit()
    audit_service.log_delete(db, user_id=actor_id, resource_type="schedule", resource_id=str(schedule.id))


async def submit_schedule_to_tito(db: Session, schedule: Schedule, callback_url: str | None = None) -> Schedule:
    employees = db.query(Employee).all()
    shift_wishes = db.query(ShiftWish).all()

    pending = [w for w in shift_wishes if w.status == "pending"]
    if pending:
        raise ValueError(
            f"Schedule has {len(pending)} pending shift wish(es). All wishes must be reviewed before submitting."
        )

    approved_wishes = [w for w in shift_wishes if w.status == "approved"]

    payload = _build_tito_payload(schedule, employees, approved_wishes, callback_url=callback_url, db=db)

    try:
        result = await tito_proxy.submit_job(payload)
        schedule.status = "submitted"
        schedule.tito_job_id = result.get("jobId") or result.get("job_id")
    except Exception:
        logger.exception("TiTO job submission failed for schedule %s", schedule.id)
        schedule.status = "failed"
        raise
    finally:
        db.add(schedule)
        db.commit()
        db.refresh(schedule)

    audit_service.log_update(
        db,
        user_id=None,
        resource_type="schedule",
        resource_id=str(schedule.id),
        details=f"submitted_to_tito job_id={schedule.tito_job_id}",
    )
    return schedule


async def retry_schedule(db: Session, schedule: Schedule, actor_id: int | None = None) -> Schedule:
    if schedule.tito_job_id:
        try:
            await tito_proxy.retry_job(schedule.tito_job_id)
            schedule.status = "submitted"
        except Exception:
            logger.exception(
                "TiTO job retry failed for schedule %s (job %s)",
                schedule.id,
                schedule.tito_job_id,
            )
            schedule.status = "failed"
            raise
        finally:
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
    else:
        await submit_schedule_to_tito(db, schedule)

    audit_service.log_update(
        db,
        user_id=actor_id,
        resource_type="schedule",
        resource_id=str(schedule.id),
        details=f"retry_tito job_id={schedule.tito_job_id}",
    )
    return schedule


def replace_all_shifts(
    db: Session,
    schedule: Schedule,
    shiftplans_data: list[ShiftplanCreate],
    actor_id: int | None = None,
) -> tuple[Schedule, ArbZgResult]:
    """Replace all shifts in a schedule and validate ArbZG compliance.

    Returns a tuple of (schedule, arbzg_result) where arbzg_result
    contains any labor law violations found in the new shifts.
    """
    db.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).delete()
    for sp_data in shiftplans_data:
        shiftplan = Shiftplan(
            schedule_id=schedule.id,
            employee_id=sp_data.employee_id,
            date=sp_data.date,
            shift_id=sp_data.shift_id,
            start_time=sp_data.start_time,
            end_time=sp_data.end_time,
            week=sp_data.week,
            break_start=sp_data.break_start,
            break_end=sp_data.break_end,
            label=sp_data.label,
            notes=sp_data.notes,
        )
        db.add(shiftplan)
    db.commit()
    db.refresh(schedule)
    audit_service.log_update(
        db,
        user_id=actor_id,
        resource_type="schedule",
        resource_id=str(schedule.id),
        details="replace_all_shifts",
    )

    # Validate ArbZG compliance for the manually created shifts
    shift_dicts = [
        {
            "employee_id": sp_data.employee_id,
            "date": sp_data.date,
            "start_time": sp_data.start_time,
            "end_date": sp_data.date,
            "end_time": sp_data.end_time,
            "break_start": sp_data.break_start,
            "break_end": sp_data.break_end,
        }
        for sp_data in shiftplans_data
    ]
    arbzg_result = validate_schedule(shift_dicts)
    if not arbzg_result.is_valid:
        logger.warning(
            "ArbZG violations in schedule %s after manual shift update: %d violation(s)",
            schedule.id,
            arbzg_result.warning_count,
        )

    return schedule, arbzg_result


def get_schedule_summary(db: Session, schedule: Schedule) -> dict[str, Any]:
    shiftplans = db.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).all()
    employee_ids = set(sp.employee_id for sp in shiftplans)
    dates = [sp.date for sp in shiftplans]

    return {
        "id": schedule.id,
        "name": schedule.name,
        "status": schedule.status,
        "total_shifts": len(shiftplans),
        "total_employees": len(employee_ids),
        "date_range": (min(dates), max(dates)) if dates else None,
    }


def _get_week_type(dt: date) -> str:
    """Determine if a date falls in week A or B based on reference date (Jan 1, 2024 = Week A, Monday)."""
    monday = dt - timedelta(days=dt.weekday())
    reference = date(2024, 1, 1)
    weeks_diff = (monday - reference).days // 7
    return "A" if weeks_diff % 2 == 0 else "B"


def _build_tito_payload(
    schedule: Schedule,
    employees: list[Employee],
    shift_wishes: list[ShiftWish],
    callback_url: str | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    """Build a payload matching the TiTO JobPayload schema."""
    if not schedule.start_date or not schedule.end_date:
        raise ValueError("Schedule must have start_date and end_date to submit to TiTO")

    # Load role name map (for skills resolution)
    role_name_by_id: dict[int, str] = {}
    if db is not None:
        role_name_by_id = {r.id: r.name for r in db.query(Role).all()}

    shift_templates = _build_shift_templates(schedule)

    employee_list = []
    for emp in employees:
        contract_hours = 40.0
        break_minutes = 30
        role = None
        if emp.contracts:
            c = emp.contracts[0]
            contract_hours = c.weekly_working_hours
            break_minutes = c.break_time
            role = c.hired_role

        current_balance = 0.0
        if db is not None:
            latest_timecard = (
                db.query(Timecard)
                .filter(Timecard.employee_id == emp.id)
                .order_by(Timecard.year.desc(), Timecard.week.desc())
                .first()
            )
            if latest_timecard:
                current_balance = latest_timecard.balance

        entry: dict[str, Any] = {
            "id": f"emp_{emp.id:03d}",
            "name": f"{emp.first_name} {emp.last_name}",
            "contractHours": contract_hours,
            "breakMinutes": break_minutes,
            "currentBalanceHours": current_balance,
            "skills": [r.name for r in emp.roles],
        }
        if role:
            entry["role"] = role
        if emp.max_work_hours is not None:
            entry["maxDailyHours"] = emp.max_work_hours
        employee_list.append(entry)

    wishes_list = []
    for wish in shift_wishes:
        wishes_list.append(
            {
                "employeeId": f"emp_{wish.employee_id:03d}",
                "date": wish.date.isoformat(),
                "type": wish.type,
                "comment": wish.note or "",
            }
        )

    # Build requirements from shift_templates or role_requirements.
    # Iterate per-date, filtering by week_type if scoped to A or B.
    requirements = []
    if schedule.shift_templates:
        current = schedule.start_date
        while current <= schedule.end_date:
            if schedule.week_type and _get_week_type(current) != schedule.week_type:
                current += timedelta(days=1)
                continue
            for st in schedule.shift_templates:
                for role_id_str, count in st.get("requirements", {}).items():
                    if int(count) > 0:
                        role_id = int(role_id_str)
                        skill_name = role_name_by_id.get(role_id) or f"ROLE_{role_id_str}"
                        requirements.append(
                            {
                                "shiftTemplateId": st["id"],
                                "shiftId": st["id"],
                                "date": current.isoformat(),
                                "count": int(count),
                                "skills": [skill_name],
                            }
                        )
            current += timedelta(days=1)

    elif schedule.role_requirements:
        current = schedule.start_date
        while current <= schedule.end_date:
            if schedule.week_type and _get_week_type(current) != schedule.week_type:
                current += timedelta(days=1)
                continue
            for role_name, count in schedule.role_requirements.items():
                if count and int(count) > 0:
                    requirements.append(
                        {
                            "shiftTemplateId": role_name,
                            "shiftId": role_name,
                            "date": current.isoformat(),
                            "count": int(count),
                        }
                    )
            current += timedelta(days=1)

    if callback_url:
        cb_url = callback_url.rstrip("/") + "/api/v1/callbacks/tito"
    else:
        cb_url = settings.backend_callback_url.rstrip("/") + "/api/v1/callbacks/tito"
    if settings.tito_api_key:
        cb_url += f"?api_key={settings.tito_api_key}"

    return {
        "metadata": {
            "tenantId": 1,
            "tenant_id": 1,
            "callback_url": cb_url,
            "idempotency_key": f"schedule_{schedule.id}",
        },
        "config": {
            "startDate": schedule.start_date.isoformat(),
            "endDate": schedule.end_date.isoformat(),
        },
        "shiftTemplates": shift_templates,
        "requirements": requirements,
        "employees": employee_list,
        "wishes": wishes_list,
    }


def _build_shift_templates(schedule: Schedule) -> list[dict[str, Any]]:
    """Derive shift templates from shift_templates, existing shiftplans, or role_requirements."""
    if schedule.shift_templates:
        return [
            {
                "id": st["id"],
                "name": st.get("name", st["id"]),
                "startTime": st["startTime"],
                "endTime": st["endTime"],
            }
            for st in schedule.shift_templates
        ]

    if schedule.shiftplans:
        seen: dict[str, dict[str, Any]] = {}
        for sp in schedule.shiftplans:
            if sp.shift_id not in seen:
                seen[sp.shift_id] = {
                    "id": sp.shift_id,
                    "name": sp.shift_id,
                    "startTime": sp.start_time.strftime("%H:%M"),
                    "endTime": sp.end_time.strftime("%H:%M"),
                }
        return list(seen.values())

    if schedule.role_requirements:
        default_times: dict[str, tuple[str, str]] = {
            "früh": ("06:00", "14:00"),
            "spät": ("14:00", "22:00"),
            "nacht": ("22:00", "06:00"),
            "early": ("06:00", "14:00"),
            "late": ("14:00", "22:00"),
            "night": ("22:00", "06:00"),
        }
        templates = []
        for role_name in schedule.role_requirements:
            times = default_times.get(role_name.lower(), ("08:00", "16:00"))
            templates.append(
                {
                    "id": role_name,
                    "name": role_name,
                    "startTime": times[0],
                    "endTime": times[1],
                }
            )
        return templates

    return []
