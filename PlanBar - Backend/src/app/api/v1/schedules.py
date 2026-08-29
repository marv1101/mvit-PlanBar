from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.requests import ShiftWishResponse
from app.core.exceptions import NotFoundException
from app.core.versioning import ConflictError, check_etag_conflict, set_etag_header, set_etag_response
from app.db.models.employee import Employee
from app.db.models.schedule import Shiftplan
from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User
from app.dependencies import get_current_user, get_db, require_admin_or_planer
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.schedule import (
    ArbZgViolationResponse,
    ScheduleCreate,
    ScheduleResponse,
    ScheduleSummary,
    ScheduleUpdate,
    ScheduleWithArbzgResponse,
    ShiftplanBatchReplace,
    ShiftplanResponse,
    ShiftplanUpdate,
)
from app.services.arbzg_validator import validate_schedule
from app.services.notification_service import create_notification_and_push
from app.services.schedule_service import (
    assert_team_write_on_shiftplans,
    create_schedule,
    delete_schedule,
    get_schedule_by_id,
    get_schedule_for_user,
    get_schedule_summary,
    list_schedules_for,
    replace_all_shifts,
    retry_schedule,
    submit_schedule_to_tito,
    update_schedule,
)


class SubmitRequest(BaseModel):
    maximize_staffing: bool = False


router = APIRouter()


def _build_shift_dicts_from_schedule(schedule) -> list[dict]:
    return [
        {
            "employee_id": sp.employee_id,
            "date": sp.date,
            "start_time": sp.start_time,
            "end_date": sp.date,
            "end_time": sp.end_time,
            "break_start": sp.break_start,
            "break_end": sp.break_end,
        }
        for sp in schedule.shiftplans
    ]


def _build_schedule_with_arbzg_response(schedule) -> ScheduleWithArbzgResponse:
    shift_dicts = _build_shift_dicts_from_schedule(schedule)
    arbzg_result = validate_schedule(shift_dicts) if shift_dicts else None
    warnings = [
        ArbZgViolationResponse(
            rule=v.rule,
            message=v.message,
            employee_id=v.employee_id,
            shift_date=v.shift_date,
            details=v.details,
        )
        for v in (arbzg_result.violations if arbzg_result else [])
    ]
    return ScheduleWithArbzgResponse(
        id=schedule.id,
        name=schedule.name,
        status=schedule.status,
        week_type=schedule.week_type,
        start_date=schedule.start_date,
        end_date=schedule.end_date,
        role_requirements=schedule.role_requirements,
        shift_templates=schedule.shift_templates,
        tito_job_id=schedule.tito_job_id,
        metadata_json=schedule.metadata_json,
        metrics_json=schedule.metrics_json,
        diagnostics_json=schedule.diagnostics_json,
        shiftplans=schedule.shiftplans,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
        arbZgWarnings=warnings,
    )


@router.post("", response_model=ScheduleWithArbzgResponse, status_code=status.HTTP_201_CREATED)
def create_schedule_endpoint(
    data: ScheduleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_planer),
):
    # Planners can only reference employees from their own teams
    try:
        assert_team_write_on_shiftplans(db, data.shiftplans, user)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Planer may only schedule for employees in their own teams",
        )
    schedule = create_schedule(db, data, user.id)
    return _build_schedule_with_arbzg_response(schedule)


@router.get("", response_model=PaginatedResponse[ScheduleResponse])
def list_schedules_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
):
    items = list_schedules_for(db, current_user)
    total = len(items)
    items_page = items[pagination.offset : pagination.offset + pagination.limit]
    return PaginatedResponse(items=items_page, total=total, offset=pagination.offset, limit=pagination.limit)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    response: Response = None,
):
    try:
        schedule = get_schedule_for_user(db, schedule_id, current_user)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Schedule is not in your team scope",
        )
    if response is not None:
        set_etag_header(response, schedule, "name", "status", "week_type")
    return schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule_endpoint(
    schedule_id: int,
    data: ScheduleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_planer),
    if_match: str | None = Header(None, alias="If-Match"),
    response: Response = None,
):
    try:
        schedule = get_schedule_for_user(db, schedule_id, user)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Schedule is not in your team scope",
        )

    try:
        check_etag_conflict(schedule, if_match, "name", "status", "week_type")
    except ConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Schedule was modified by another user. Please refresh and try again.",
        )

    updated = update_schedule(db, schedule, data, actor_id=user.id)
    if response is not None:
        set_etag_response(response, updated, "name", "status", "week_type")
    return updated


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_planer),
):
    try:
        schedule = get_schedule_for_user(db, schedule_id, user)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Schedule is not in your team scope",
        )
    delete_schedule(db, schedule, actor_id=user.id)


@router.post("/{schedule_id}/submit", response_model=ScheduleResponse)
async def submit_schedule_endpoint(
    schedule_id: int,
    body: SubmitRequest = SubmitRequest(),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_planer),
):
    try:
        schedule = get_schedule_for_user(db, schedule_id, user)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Schedule is not in your team scope",
        )
    try:
        return await submit_schedule_to_tito(db, schedule, user=user, maximize_staffing=body.maximize_staffing)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{schedule_id}/retry", response_model=ScheduleResponse)
async def retry_schedule_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_planer),
):
    try:
        schedule = get_schedule_for_user(db, schedule_id, user)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Schedule is not in your team scope",
        )
    return await retry_schedule(db, schedule, actor_id=user.id)


@router.get("/{schedule_id}/summary", response_model=ScheduleSummary)
def get_schedule_summary_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        schedule = get_schedule_for_user(db, schedule_id, current_user)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Schedule is not in your team scope",
        )
    return get_schedule_summary(db, schedule)


@router.get("/{schedule_id}/shifts", response_model=PaginatedResponse[ShiftplanResponse])
def get_schedule_shifts(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
):
    try:
        schedule = get_schedule_for_user(db, schedule_id, current_user)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Schedule is not in your team scope",
        )
    total = len(schedule.shiftplans)
    items = schedule.shiftplans[pagination.offset : pagination.offset + pagination.limit]
    return PaginatedResponse(items=items, total=total, offset=pagination.offset, limit=pagination.limit)


@router.put("/{schedule_id}/shifts/{shiftplan_id}", response_model=ScheduleWithArbzgResponse)
def update_shiftplan(
    schedule_id: int,
    shiftplan_id: int,
    data: ShiftplanUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_planer),
):
    try:
        schedule = get_schedule_for_user(db, schedule_id, user)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Schedule is not in your team scope",
        )
    shiftplan = (
        db.query(Shiftplan)
        .filter(
            Shiftplan.id == shiftplan_id,
            Shiftplan.schedule_id == schedule_id,
        )
        .first()
    )
    if not shiftplan:
        raise NotFoundException(detail="Shiftplan not found")

    # If the planner reassigns to a foreign employee: blocked
    new_employee_ids = {shiftplan.employee_id}
    if data.employee_id is not None:
        new_employee_ids = {data.employee_id}
    try:
        # Validate that shiftplan would still be in scope after the change.
        from app.services.schedule_service import _assert_team_restriction_for_employee_ids

        _assert_team_restriction_for_employee_ids(db, new_employee_ids, user)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Planer may only assign employees from their own teams",
        )
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
    if data.break_start is not None:
        shiftplan.break_start = data.break_start
    if data.break_end is not None:
        shiftplan.break_end = data.break_end
    if data.label is not None:
        shiftplan.label = data.label
    if data.notes is not None:
        shiftplan.notes = data.notes
    db.add(shiftplan)
    db.commit()
    db.refresh(shiftplan)

    # Notify the employee about the shift change
    employee = db.query(Employee).filter(Employee.id == shiftplan.employee_id).first()
    if employee and employee.user_id:
        create_notification_and_push(
            db=db,
            user_id=employee.user_id,
            notification_type="shift_changed",
            title="Schicht geändert",
            message=f"Deine Schicht am {shiftplan.date} wurde geändert.",
            data={
                "shiftplan_id": shiftplan.id,
                "schedule_id": schedule_id,
                "date": str(shiftplan.date),
                "shift_id": shiftplan.shift_id,
            },
            push_url="/employee-view",
            push_tag="shift_changed",
        )

    # Reload schedule with all shiftplans for ArbZG validation and full response
    schedule = get_schedule_by_id(db, schedule_id)
    return _build_schedule_with_arbzg_response(schedule)


@router.put("/{schedule_id}/shifts", response_model=ScheduleWithArbzgResponse)
def replace_all_shifts_endpoint(
    schedule_id: int,
    data: ShiftplanBatchReplace,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_planer),
):
    try:
        schedule = get_schedule_for_user(db, schedule_id, user)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Schedule is not in your team scope",
        )
    try:
        assert_team_write_on_shiftplans(db, data.shiftplans, user)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Planer may only schedule for employees in their own teams",
        )
    schedule, arbzg_result = replace_all_shifts(db, schedule, data.shiftplans, actor_id=user.id)
    warnings = [
        ArbZgViolationResponse(
            rule=v.rule,
            message=v.message,
            employee_id=v.employee_id,
            shift_date=v.shift_date,
            details=v.details,
        )
        for v in arbzg_result.violations
    ]
    return ScheduleWithArbzgResponse(
        id=schedule.id,
        name=schedule.name,
        status=schedule.status,
        start_date=schedule.start_date,
        end_date=schedule.end_date,
        role_requirements=schedule.role_requirements,
        shift_templates=schedule.shift_templates,
        tito_job_id=schedule.tito_job_id,
        metadata_json=schedule.metadata_json,
        metrics_json=schedule.metrics_json,
        diagnostics_json=schedule.diagnostics_json,
        shiftplans=schedule.shiftplans,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
        arbZgWarnings=warnings,
    )


@router.get("/{schedule_id}/wishes/pending", response_model=PaginatedResponse[ShiftWishResponse])
def get_pending_wishes(
    schedule_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_planer),
    pagination: PaginationParams = Depends(),
):
    try:
        schedule = get_schedule_for_user(db, schedule_id, user)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Schedule is not in your team scope",
        )

    query = (
        db.query(ShiftWish)
        .filter(
            ShiftWish.status == "pending",
            ShiftWish.date >= schedule.start_date,
            ShiftWish.date <= schedule.end_date,
        )
        .order_by(ShiftWish.date)
    )
    if user.role == "planer":
        from app.services import team_service

        team_ids = team_service.get_team_ids_for_user(db, user)
        if team_ids:
            query = team_service.filter_query_by_team_scope(query, ShiftWish, team_ids)
        else:
            query = query.filter(ShiftWish.employee_id == -1)
    total = query.count()
    items = query.offset(pagination.offset).limit(pagination.limit).all()
    return PaginatedResponse(items=items, total=total, offset=pagination.offset, limit=pagination.limit)


@router.get("/{schedule_id}/wishes", response_model=PaginatedResponse[ShiftWishResponse])
def get_wishes_by_status(
    schedule_id: int,
    status: str = Query(default="approved", pattern="^(pending|approved|rejected)$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_planer),
    pagination: PaginationParams = Depends(),
):
    """Get wishes for a schedule filtered by status.

    Used by EditableScheduleCalendar to show approved wishes as overlays.
    Only approved wishes are displayed in the calendar by default.
    """
    try:
        schedule = get_schedule_for_user(db, schedule_id, user)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Schedule is not in your team scope",
        )
    query = (
        db.query(ShiftWish)
        .filter(
            ShiftWish.status == status,
            ShiftWish.date >= schedule.start_date,
            ShiftWish.date <= schedule.end_date,
        )
        .order_by(ShiftWish.date)
    )
    if user.role == "planer":
        from app.services import team_service

        team_ids = team_service.get_team_ids_for_user(db, user)
        if team_ids:
            query = team_service.filter_query_by_team_scope(query, ShiftWish, team_ids)
        else:
            query = query.filter(ShiftWish.employee_id == -1)
    total = query.count()
    items = query.offset(pagination.offset).limit(pagination.limit).all()
    return PaginatedResponse(items=items, total=total, offset=pagination.offset, limit=pagination.limit)
