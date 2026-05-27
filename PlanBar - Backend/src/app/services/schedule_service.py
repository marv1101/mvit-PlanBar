from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models.employee import Employee
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.shift_wish import ShiftWish
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ShiftplanCreate
from app.services.tito_proxy import tito_proxy


def create_schedule(db: Session, data: ScheduleCreate, user_id: int | None = None) -> Schedule:
    schedule = Schedule(
        name=data.name,
        week_type=data.week_type,
        start_date=data.start_date,
        end_date=data.end_date,
        role_requirements=data.role_requirements,
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
            notes=shiftplan_data.notes,
        )
        db.add(shiftplan)

    db.commit()
    db.refresh(schedule)
    return schedule


def get_schedule_by_id(db: Session, schedule_id: int) -> Schedule | None:
    return db.query(Schedule).filter(Schedule.id == schedule_id).first()


def list_schedules(db: Session) -> list[Schedule]:
    return db.query(Schedule).order_by(Schedule.created_at.desc()).all()


def update_schedule(db: Session, schedule: Schedule, data: ScheduleUpdate) -> Schedule:
    if data.name is not None:
        schedule.name = data.name
    if data.week_type is not None:
        schedule.week_type = data.week_type
    if data.status is not None:
        schedule.status = data.status.value
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def delete_schedule(db: Session, schedule: Schedule) -> None:
    db.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).delete()
    db.delete(schedule)
    db.commit()


async def submit_schedule_to_tito(db: Session, schedule: Schedule, callback_url: str | None = None) -> Schedule:
    employees = db.query(Employee).all()
    shift_wishes = db.query(ShiftWish).all()

    payload = _build_tito_payload(schedule, employees, shift_wishes, callback_url=callback_url)

    try:
        result = await tito_proxy.submit_job(payload)
        schedule.status = "submitted"
        schedule.tito_job_id = result.get("job_id")
    except Exception:
        schedule.status = "failed"
        raise
    finally:
        db.add(schedule)
        db.commit()
        db.refresh(schedule)

    return schedule


async def retry_schedule(db: Session, schedule: Schedule) -> Schedule:
    if schedule.tito_job_id:
        try:
            await tito_proxy.retry_job(schedule.tito_job_id)
            schedule.status = "submitted"
        except Exception:
            schedule.status = "failed"
            raise
        finally:
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
    else:
        await submit_schedule_to_tito(db, schedule)

    return schedule


def replace_all_shifts(
    db: Session,
    schedule: Schedule,
    shiftplans_data: list[ShiftplanCreate],
) -> Schedule:
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
            notes=sp_data.notes,
        )
        db.add(shiftplan)
    db.commit()
    db.refresh(schedule)
    return schedule


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


def _build_tito_payload(
    schedule: Schedule,
    employees: list[Employee],
    shift_wishes: list[ShiftWish],
    callback_url: str | None = None,
) -> dict[str, Any]:
    """Build a payload matching the TiTO JobPayload schema."""
    if not schedule.start_date or not schedule.end_date:
        raise ValueError("Schedule must have start_date and end_date to submit to TiTO")

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

        entry: dict[str, Any] = {
            "id": f"emp_{emp.id:03d}",
            "name": f"{emp.first_name} {emp.last_name}",
            "contractHours": contract_hours,
            "breakMinutes": break_minutes,
        }
        if role:
            entry["role"] = role
        if emp.max_work_hours is not None:
            entry["maxDailyHours"] = emp.max_work_hours
        employee_list.append(entry)

    wishes_list = []
    for wish in shift_wishes:
        wishes_list.append({
            "employeeId": f"emp_{wish.employee_id:03d}",
            "date": wish.date.isoformat(),
            "type": wish.type,
            "comment": wish.note or "",
        })

    # Expand role_requirements into per-date requirements
    requirements = []
    if schedule.role_requirements:
        current = schedule.start_date
        while current <= schedule.end_date:
            for role_name, count in schedule.role_requirements.items():
                if count and int(count) > 0:
                    requirements.append({
                        "shiftTemplateId": role_name,
                        "shiftId": role_name,
                        "date": current.isoformat(),
                        "count": int(count),
                    })
            current += timedelta(days=1)

    if callback_url:
        cb_url = callback_url.rstrip("/") + "/api/v1/callbacks/tito"
    else:
        cb_url = settings.backend_callback_url.rstrip("/") + "/api/v1/callbacks/tito"

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
    """Derive shift templates from existing shiftplans or role_requirements."""
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
            templates.append({
                "id": role_name,
                "name": role_name,
                "startTime": times[0],
                "endTime": times[1],
            })
        return templates

    return []
