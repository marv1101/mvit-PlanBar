from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.requests import ShiftWishResponse
from app.core.exceptions import NotFoundException
from app.dependencies import get_current_user, get_db, require_admin
from app.db.models.schedule import Shiftplan
from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleResponse,
    ScheduleSummary,
    ScheduleUpdate,
    ShiftplanBatchReplace,
    ShiftplanResponse,
    ShiftplanUpdate,
)
from app.services.schedule_service import (
    create_schedule,
    delete_schedule,
    get_schedule_by_id,
    get_schedule_summary,
    list_schedules,
    replace_all_shifts,
    retry_schedule,
    submit_schedule_to_tito,
    update_schedule,
)

router = APIRouter()


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule_endpoint(
    data: ScheduleCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return create_schedule(db, data, admin.id)


@router.get("", response_model=list[ScheduleResponse])
def list_schedules_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_schedules(db)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = get_schedule_by_id(db, schedule_id)
    if not schedule:
        raise NotFoundException(detail="Schedule not found")
    return schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule_endpoint(
    schedule_id: int,
    data: ScheduleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    schedule = get_schedule_by_id(db, schedule_id)
    if not schedule:
        raise NotFoundException(detail="Schedule not found")
    return update_schedule(db, schedule, data, actor_id=admin.id)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    schedule = get_schedule_by_id(db, schedule_id)
    if not schedule:
        raise NotFoundException(detail="Schedule not found")
    delete_schedule(db, schedule, actor_id=admin.id)


@router.post("/{schedule_id}/submit", response_model=ScheduleResponse)
async def submit_schedule_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    schedule = get_schedule_by_id(db, schedule_id)
    if not schedule:
        raise NotFoundException(detail="Schedule not found")
    try:
        return await submit_schedule_to_tito(db, schedule)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{schedule_id}/retry", response_model=ScheduleResponse)
async def retry_schedule_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    schedule = get_schedule_by_id(db, schedule_id)
    if not schedule:
        raise NotFoundException(detail="Schedule not found")
    return await retry_schedule(db, schedule, actor_id=admin.id)


@router.get("/{schedule_id}/summary", response_model=ScheduleSummary)
def get_schedule_summary_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = get_schedule_by_id(db, schedule_id)
    if not schedule:
        raise NotFoundException(detail="Schedule not found")
    return get_schedule_summary(db, schedule)


@router.get("/{schedule_id}/shifts", response_model=list[ShiftplanResponse])
def get_schedule_shifts(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = get_schedule_by_id(db, schedule_id)
    if not schedule:
        raise NotFoundException(detail="Schedule not found")
    return schedule.shiftplans


@router.put("/{schedule_id}/shifts/{shiftplan_id}", response_model=ShiftplanResponse)
def update_shiftplan(
    schedule_id: int,
    shiftplan_id: int,
    data: ShiftplanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    shiftplan = db.query(Shiftplan).filter(
        Shiftplan.id == shiftplan_id,
        Shiftplan.schedule_id == schedule_id,
    ).first()
    if not shiftplan:
        raise NotFoundException(detail="Shiftplan not found")
    if data.employee_id is not None:
        shiftplan.employee_id = data.employee_id
    if data.date is not None:
        shiftplan.date = data.date
    if data.shift_id is not None:
        shiftplan.shift_id = data.shift_id
    if data.start_time is not None:
        shiftplan.start_time = data.start_time
    if data.end_time is not None:
        shiftplan.end_time = data.end_time
    if data.week is not None:
        shiftplan.week = data.week
    if data.notes is not None:
        shiftplan.notes = data.notes
    db.add(shiftplan)
    db.commit()
    db.refresh(shiftplan)
    return shiftplan


@router.put("/{schedule_id}/shifts", response_model=ScheduleResponse)
def replace_all_shifts_endpoint(
    schedule_id: int,
    data: ShiftplanBatchReplace,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = get_schedule_by_id(db, schedule_id)
    if not schedule:
        raise NotFoundException(detail="Schedule not found")
    return replace_all_shifts(db, schedule, data.shiftplans, actor_id=current_user.id)


@router.get("/{schedule_id}/wishes/pending", response_model=list[ShiftWishResponse])
def get_pending_wishes(
    schedule_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    schedule = get_schedule_by_id(db, schedule_id)
    if not schedule:
        raise NotFoundException(detail="Schedule not found")
    wishes = db.query(ShiftWish).filter(
        ShiftWish.status == "pending",
        ShiftWish.date >= schedule.start_date,
        ShiftWish.date <= schedule.end_date,
    ).order_by(ShiftWish.date).all()
    return wishes
