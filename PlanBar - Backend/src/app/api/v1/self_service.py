from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.dependencies import get_current_user, get_db
from app.db.models.availability import Availability
from app.db.models.employee import Employee, Timecard
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.user import User
from app.schemas.availability import AvailabilityEntry, AvailabilityResponse, AvailabilityUpdate
from app.schemas.self_service import MyOvertimeResponse, MyShiftResponse

router = APIRouter()


@router.get("/schedule", response_model=list[MyShiftResponse])
def get_my_schedule(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.employee_id:
        return []

    shiftplans = (
        db.query(Shiftplan)
        .filter(Shiftplan.employee_id == current_user.employee_id)
        .order_by(Shiftplan.date.asc())
        .all()
    )

    result = []
    for sp in shiftplans:
        schedule = db.query(Schedule).filter(Schedule.id == sp.schedule_id).first()
        result.append(
            MyShiftResponse(
                id=sp.id,
                schedule_id=sp.schedule_id,
                schedule_name=schedule.name if schedule else "",
                date=str(sp.date),
                start_time=str(sp.start_time),
                end_time=str(sp.end_time),
                week=sp.week,
                break_start=sp.break_start,
                break_end=sp.break_end,
                label=sp.label,
            )
        )
    return result


@router.get("/overtime", response_model=MyOvertimeResponse)
def get_my_overtime(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.employee_id:
        return MyOvertimeResponse()

    latest_timecard = (
        db.query(Timecard)
        .filter(Timecard.employee_id == current_user.employee_id)
        .order_by(Timecard.year.desc(), Timecard.week.desc())
        .first()
    )

    if not latest_timecard:
        return MyOvertimeResponse()

    return MyOvertimeResponse(
        current_balance=latest_timecard.balance,
        scheduled_hours=latest_timecard.scheduled_hours,
        contract_hours=latest_timecard.contract_hours,
        week=latest_timecard.week,
        year=latest_timecard.year,
    )


@router.put("/availability", response_model=list[AvailabilityResponse])
def update_my_availability(
    data: AvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.employee_id:
        raise NotFoundException(detail="Current user has no linked employee")

    responses = []
    for entry in data.entries:
        avail = (
            db.query(Availability)
            .filter(
                Availability.employee_id == current_user.employee_id,
                Availability.day_of_week == entry.day_of_week,
            )
            .first()
        )
        if avail:
            avail.available = entry.available
            avail.note = entry.note
        else:
            avail = Availability(
                employee_id=current_user.employee_id,
                day_of_week=entry.day_of_week,
                available=entry.available,
                note=entry.note,
            )
            db.add(avail)
        db.flush()
        responses.append(avail)

    db.commit()
    for r in responses:
        db.refresh(r)
    return responses


@router.get("/availability", response_model=list[AvailabilityResponse])
def get_my_availability(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.employee_id:
        return []

    availabilities = (
        db.query(Availability)
        .filter(Availability.employee_id == current_user.employee_id)
        .order_by(Availability.day_of_week.asc())
        .all()
    )
    return availabilities
