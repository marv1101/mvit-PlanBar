from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models.employee import Employee
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.shift_wish import ShiftWish
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ShiftplanCreate
from app.schemas.tito import TiTOJobRequest, TiTORequestMetadata
from app.services.tito_proxy import tito_proxy


def create_schedule(db: Session, data: ScheduleCreate, user_id: int | None = None) -> Schedule:
    schedule = Schedule(
        name=data.name,
        week_type=data.week_type,
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
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def delete_schedule(db: Session, schedule: Schedule) -> None:
    db.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).delete()
    db.delete(schedule)
    db.commit()


async def submit_schedule_to_tito(db: Session, schedule: Schedule) -> Schedule:
    employees = db.query(Employee).all()
    shift_wishes = db.query(ShiftWish).all()

    payload = _build_tito_payload(schedule, employees, shift_wishes)

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
) -> dict[str, Any]:
    employee_list = []
    for emp in employees:
        contracts = [{"weeklyWorkingHours": c.weekly_working_hours, "breakTime": c.break_time} for c in emp.contracts]
        employee_list.append({
            "employeeId": f"emp_{emp.id:03d}",
            "name": f"{emp.first_name} {emp.last_name}",
            "contracts": contracts if contracts else [{"weeklyWorkingHours": 40, "breakTime": 30}],
        })

    wishes_list = []
    for wish in shift_wishes:
        wishes_list.append({
            "employeeId": f"emp_{wish.employee_id:03d}",
            "date": wish.date.isoformat(),
            "type": wish.type,
            "note": wish.note or "",
        })

    metadata = TiTORequestMetadata(
        callback_url=f"{settings.backend_callback_url}/api/v1/callbacks/tito",
        idempotency_key=f"schedule_{schedule.id}",
    )

    return TiTOJobRequest(
        employees=employee_list,
        shiftWishes=wishes_list,
        requirements=[],
        constraints={},
        metadata=metadata,
    ).model_dump()
