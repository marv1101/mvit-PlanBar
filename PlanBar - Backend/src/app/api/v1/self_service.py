from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.db.models.availability import Availability
from app.db.models.employee import Employee, Timecard
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.user import User
from app.dependencies import get_current_user, get_db
from app.schemas.availability import AvailabilityResponse, AvailabilityUpdate
from app.schemas.employee import EmployeeResponse
from app.schemas.self_service import MyOvertimeResponse, MyShiftResponse
from app.schemas.team import TeamResponse
from app.services import team_service

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
                employee_id=sp.employee_id,
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


@router.get("/teams", response_model=list[TeamResponse])
def get_my_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the teams the current user belongs to."""
    teams = team_service.get_teams_for_user(db, current_user)
    return teams


@router.get("/team-schedule", response_model=list[MyShiftResponse])
def get_my_team_schedule(
    schedule_id: int = Query(..., description="Schedule ID to view team shifts for"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return shifts for a schedule that belong to colleagues in the same team(s)."""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise NotFoundException(detail="Schedule not found")

    team_ids = team_service.get_team_ids_for_user(db, current_user)
    if not team_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to any team",
        )

    shiftplans = team_service.filter_query_by_team_scope(
        db.query(Shiftplan).filter(Shiftplan.schedule_id == schedule_id),
        Shiftplan,
        team_ids,
    ).order_by(Shiftplan.date.asc()).all()

    result = []
    for sp in shiftplans:
        result.append(
            MyShiftResponse(
                id=sp.id,
                schedule_id=sp.schedule_id,
                schedule_name=schedule.name,
                employee_id=sp.employee_id,
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


@router.get("/team-employees", response_model=list[EmployeeResponse])
def get_my_team_employees(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return employees that belong to the same team(s) as the current user."""
    team_ids = team_service.get_team_ids_for_user(db, current_user)
    if not team_ids:
        return []
    employees = team_service.filter_query_by_team_scope(
        db.query(Employee), Employee, team_ids
    ).distinct().order_by(Employee.last_name, Employee.first_name).all()
    return employees


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
