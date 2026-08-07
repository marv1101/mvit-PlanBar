from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.core.versioning import ConflictError, check_etag_conflict, set_etag_header, set_etag_response
from app.db.models.employee import Contract, Employee, Timecard
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.user import User
from app.dependencies import get_current_user, get_db, require_admin
from app.schemas.employee import (
    ContractCreate,
    ContractResponse,
    ContractUpdate,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    TimeAccountAdjust,
    TimeAccountEntry,
    TimeAccountProjected,
    TimeAccountResponse,
    TimecardCreate,
    TimecardResponse,
    TimecardUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.employee_service import (
    create_contract,
    create_employee,
    create_timecard,
    delete_employee,
    get_contract_by_id,
    get_employee_by_id,
    get_timecard_by_id,
    list_contracts,
    list_employees,
    list_timecards,
    update_contract,
    update_employee,
    update_timecard,
)
from app.services.tito_callback import _calc_effective_hours

router = APIRouter()


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee_endpoint(
    data: EmployeeCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return create_employee(db, data, actor_id=admin.id)


@router.get("", response_model=PaginatedResponse[EmployeeResponse])
def list_employees_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
):
    if current_user.role == "admin":
        total = db.query(Employee).count()
        items = list_employees(db, offset=pagination.offset, limit=pagination.limit)
    elif current_user.role == "planer":
        from app.services import team_service

        team_ids = team_service.get_team_ids_for_user(db, current_user)
        if not team_ids:
            query = db.query(Employee).filter(False)
            total = 0
            items = []
        else:
            query = team_service.filter_query_by_team_scope(db.query(Employee), Employee, team_ids).distinct()
            total = query.count()
            items = query.offset(pagination.offset).limit(pagination.limit).all()
    else:
        query = db.query(Employee).filter(Employee.id == current_user.employee_id)
        total = query.count()
        items = query.offset(pagination.offset).limit(pagination.limit).all()
    return PaginatedResponse(items=items, total=total, offset=pagination.offset, limit=pagination.limit)


@router.get("/time-accounts", response_model=PaginatedResponse[TimeAccountResponse])
def get_all_time_accounts(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    pagination: PaginationParams = Depends(),
):
    total = db.query(Employee).count()
    employees = list_employees(db, offset=pagination.offset, limit=pagination.limit)
    items = [_build_time_account_response(emp, db) for emp in employees]
    return PaginatedResponse(items=items, total=total, offset=pagination.offset, limit=pagination.limit)


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee_endpoint(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    response: Response = None,
):
    employee = get_employee_by_id(db, employee_id)
    if not employee:
        raise NotFoundException(detail="Employee not found")
    from app.services import team_service

    try:
        team_service.assert_user_can_access_employee(db, current_user, employee_id)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        ) from e
    if response is not None:
        set_etag_header(response, employee, "first_name", "last_name", "email")
    return employee


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee_endpoint(
    employee_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    if_match: str | None = Header(None, alias="If-Match"),
    response: Response = None,
):
    employee = get_employee_by_id(db, employee_id)
    if not employee:
        raise NotFoundException(detail="Employee not found")
    try:
        check_etag_conflict(employee, if_match, "first_name", "last_name", "email")
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee was modified by another user. Please refresh and try again.",
        ) from e
    updated = update_employee(db, employee, data, actor_id=admin.id)
    if response is not None:
        set_etag_response(response, updated, "first_name", "last_name", "email")
    return updated


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee_endpoint(
    employee_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    employee = get_employee_by_id(db, employee_id)
    if not employee:
        raise NotFoundException(detail="Employee not found")
    delete_employee(db, employee, actor_id=admin.id)


contract_router = APIRouter()


@contract_router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
def create_contract_endpoint(
    data: ContractCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return create_contract(db, data, actor_id=admin.id)


@contract_router.get("", response_model=PaginatedResponse[ContractResponse])
def list_contracts_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
):
    if current_user.role == "admin":
        total = db.query(Contract).count()
        items = list_contracts(db, offset=pagination.offset, limit=pagination.limit)
    elif current_user.role == "user":
        query = db.query(Contract).join(Employee).filter(Employee.id == current_user.employee_id)
        total = query.count()
        items = query.offset(pagination.offset).limit(pagination.limit).all()
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    return PaginatedResponse(items=items, total=total, offset=pagination.offset, limit=pagination.limit)


@contract_router.get("/{contract_id}", response_model=ContractResponse)
def get_contract_endpoint(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = get_contract_by_id(db, contract_id)
    if not contract:
        raise NotFoundException(detail="Contract not found")
    from app.services import team_service

    try:
        team_service.assert_user_can_access_employee(db, current_user, contract.employee_id, allow_planer=False)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        ) from e
    return contract


@contract_router.put("/{contract_id}", response_model=ContractResponse)
def update_contract_endpoint(
    contract_id: int,
    data: ContractUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    contract = get_contract_by_id(db, contract_id)
    if not contract:
        raise NotFoundException(detail="Contract not found")
    return update_contract(db, contract, data, actor_id=admin.id)


timecard_router = APIRouter()


@timecard_router.post("", response_model=TimecardResponse, status_code=status.HTTP_201_CREATED)
def create_timecard_endpoint(
    data: TimecardCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return create_timecard(db, data, actor_id=admin.id)


@timecard_router.get("", response_model=PaginatedResponse[TimecardResponse])
def list_timecards_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
):
    if current_user.role == "admin":
        total = db.query(Timecard).count()
        items = list_timecards(db, offset=pagination.offset, limit=pagination.limit)
    elif current_user.role == "user":
        query = db.query(Timecard).join(Employee).filter(Employee.id == current_user.employee_id)
        total = query.count()
        items = query.offset(pagination.offset).limit(pagination.limit).all()
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    return PaginatedResponse(items=items, total=total, offset=pagination.offset, limit=pagination.limit)


@timecard_router.get("/{timecard_id}", response_model=TimecardResponse)
def get_timecard_endpoint(
    timecard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    timecard = get_timecard_by_id(db, timecard_id)
    if not timecard:
        raise NotFoundException(detail="Timecard not found")
    from app.services import team_service

    try:
        team_service.assert_user_can_access_employee(db, current_user, timecard.employee_id, allow_planer=False)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        ) from e
    return timecard


@timecard_router.put("/{timecard_id}", response_model=TimecardResponse)
def update_timecard_endpoint(
    timecard_id: int,
    data: TimecardUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    timecard = get_timecard_by_id(db, timecard_id)
    if not timecard:
        raise NotFoundException(detail="Timecard not found")
    return update_timecard(db, timecard, data, actor_id=admin.id)


def _build_time_account_response(employee: Employee, db: Session) -> TimeAccountResponse:
    timecards = (
        db.query(Timecard)
        .filter(
            Timecard.employee_id == employee.id,
        )
        .order_by(Timecard.year.asc(), Timecard.week.asc())
        .all()
    )

    history = []
    for tc in timecards:
        delta = tc.scheduled_hours - tc.contract_hours
        total_change = delta + (tc.manual_adjustment_hours or 0.0)
        history.append(
            TimeAccountEntry(
                week=tc.week,
                year=tc.year,
                scheduled_hours=tc.scheduled_hours,
                contract_hours=tc.contract_hours,
                delta=delta,
                balance=tc.balance,
                manual_adjustment=tc.manual_adjustment_hours or 0.0,
                adjustment_reason=tc.adjustment_reason,
                total_change=total_change,
            )
        )

    current_balance = timecards[-1].balance if timecards else 0.0

    projected = None
    latest_schedule = (
        db.query(Schedule)
        .filter(
            Schedule.status == "submitted",
        )
        .order_by(Schedule.end_date.desc())
        .first()
    )

    if latest_schedule:
        shiftplans = (
            db.query(Shiftplan)
            .filter(
                Shiftplan.schedule_id == latest_schedule.id,
                Shiftplan.employee_id == employee.id,
            )
            .all()
        )
        if shiftplans:
            contract = employee.contracts[0] if employee.contracts else None
            from_schedule = sum(_calc_effective_hours(sp, contract) for sp in shiftplans)
            weekly_hours = contract.weekly_working_hours if contract else 40.0
            iso_weeks = {sp.date.isocalendar()[:2] for sp in shiftplans}
            num_weeks = len(iso_weeks)
            expected_balance_after = current_balance + from_schedule - (weekly_hours * num_weeks)
            projected = TimeAccountProjected(
                from_schedule=from_schedule,
                expected_balance_after=expected_balance_after,
            )

    return TimeAccountResponse(
        employee_id=employee.id,
        employee_name=f"{employee.first_name} {employee.last_name}",
        current_balance=current_balance,
        history=history,
        projected=projected,
    )


@router.get("/{employee_id}/time-account", response_model=TimeAccountResponse)
def get_employee_time_account(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = get_employee_by_id(db, employee_id)
    if not employee:
        raise NotFoundException(detail="Employee not found")
    from app.services import team_service

    try:
        team_service.assert_user_can_access_employee(db, current_user, employee_id, allow_planer=False)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        ) from e
    return _build_time_account_response(employee, db)


@router.post(
    "/{employee_id}/time-account/adjust",
    response_model=TimeAccountResponse,
    status_code=status.HTTP_200_OK,
)
def adjust_employee_time_account(
    employee_id: int,
    data: TimeAccountAdjust,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    employee = get_employee_by_id(db, employee_id)
    if not employee:
        raise NotFoundException(detail="Employee not found")

    latest_tc = (
        db.query(Timecard)
        .filter(
            Timecard.employee_id == employee_id,
        )
        .order_by(Timecard.year.desc(), Timecard.week.desc())
        .with_for_update()
        .first()
    )

    if latest_tc:
        latest_tc.balance = latest_tc.balance + data.delta_hours
        latest_tc.manual_adjustment_hours = (latest_tc.manual_adjustment_hours or 0) + data.delta_hours
        if data.reason:
            existing_reason = latest_tc.adjustment_reason or ""
            latest_tc.adjustment_reason = (
                f"{existing_reason}; {data.reason}".strip("; ") if existing_reason else data.reason
            )
    else:
        now_utc = datetime.now(UTC)
        tc = Timecard(
            employee_id=employee_id,
            week=now_utc.isocalendar()[1],
            year=now_utc.year,
            scheduled_hours=0.0,
            contract_hours=0.0,
            manual_adjustment_hours=data.delta_hours,
            adjustment_reason=data.reason,
            balance=data.delta_hours,
        )
        db.add(tc)
    db.commit()

    return _build_time_account_response(employee, db)
