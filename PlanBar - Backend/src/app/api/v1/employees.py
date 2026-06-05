from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.dependencies import get_current_user, get_db, require_admin
from app.db.models.employee import Contract, Employee, Timecard
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.user import User
from app.schemas.employee import (
    ContractCreate,
    ContractResponse,
    ContractUpdate,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    TimeAccountEntry,
    TimeAccountProjected,
    TimeAccountResponse,
    TimecardCreate,
    TimecardResponse,
    TimecardUpdate,
)
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
    current_user: User = Depends(get_current_user),
):
    return create_employee(db, data)


@router.get("", response_model=list[EmployeeResponse])
def list_employees_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_employees(db)


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee_endpoint(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = get_employee_by_id(db, employee_id)
    if not employee:
        raise NotFoundException(detail="Employee not found")
    return employee


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee_endpoint(
    employee_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = get_employee_by_id(db, employee_id)
    if not employee:
        raise NotFoundException(detail="Employee not found")
    return update_employee(db, employee, data)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee_endpoint(
    employee_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    employee = get_employee_by_id(db, employee_id)
    if not employee:
        raise NotFoundException(detail="Employee not found")
    delete_employee(db, employee)


contract_router = APIRouter()


@contract_router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
def create_contract_endpoint(
    data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_contract(db, data)


@contract_router.get("", response_model=list[ContractResponse])
def list_contracts_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_contracts(db)


@contract_router.get("/{contract_id}", response_model=ContractResponse)
def get_contract_endpoint(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = get_contract_by_id(db, contract_id)
    if not contract:
        raise NotFoundException(detail="Contract not found")
    return contract


@contract_router.put("/{contract_id}", response_model=ContractResponse)
def update_contract_endpoint(
    contract_id: int,
    data: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = get_contract_by_id(db, contract_id)
    if not contract:
        raise NotFoundException(detail="Contract not found")
    return update_contract(db, contract, data)


timecard_router = APIRouter()


@timecard_router.post("", response_model=TimecardResponse, status_code=status.HTTP_201_CREATED)
def create_timecard_endpoint(
    data: TimecardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_timecard(db, data)


@timecard_router.get("", response_model=list[TimecardResponse])
def list_timecards_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_timecards(db)


@timecard_router.get("/{timecard_id}", response_model=TimecardResponse)
def get_timecard_endpoint(
    timecard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    timecard = get_timecard_by_id(db, timecard_id)
    if not timecard:
        raise NotFoundException(detail="Timecard not found")
    return timecard


@timecard_router.put("/{timecard_id}", response_model=TimecardResponse)
def update_timecard_endpoint(
    timecard_id: int,
    data: TimecardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    timecard = get_timecard_by_id(db, timecard_id)
    if not timecard:
        raise NotFoundException(detail="Timecard not found")
    return update_timecard(db, timecard, data)


@router.get("/{employee_id}/time-account", response_model=TimeAccountResponse)
def get_employee_time_account(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = get_employee_by_id(db, employee_id)
    if not employee:
        raise NotFoundException(detail="Employee not found")

    timecards = db.query(Timecard).filter(
        Timecard.employee_id == employee_id,
    ).order_by(Timecard.year.asc(), Timecard.week.asc()).all()

    history = []
    for tc in timecards:
        history.append(TimeAccountEntry(
            week=tc.week,
            year=tc.year,
            scheduled_hours=tc.scheduled_hours,
            contract_hours=tc.contract_hours,
            delta=tc.scheduled_hours - tc.contract_hours,
            balance=tc.balance,
        ))

    current_balance = timecards[-1].balance if timecards else 0.0

    projected = None
    latest_schedule = db.query(Schedule).filter(
        Schedule.status.in_(["completed", "submitted"]),
    ).order_by(Schedule.end_date.desc()).first()

    if latest_schedule:
        shiftplans = db.query(Shiftplan).filter(
            Shiftplan.schedule_id == latest_schedule.id,
            Shiftplan.employee_id == employee_id,
        ).all()
        if shiftplans:
            contract = employee.contracts[0] if employee.contracts else None
            from_schedule = sum(
                _calc_effective_hours(sp, contract) for sp in shiftplans
            )
            weekly_hours = contract.weekly_working_hours if contract else 40.0
            expected_balance_after = current_balance + from_schedule - weekly_hours
            projected = TimeAccountProjected(
                from_schedule=from_schedule,
                expected_balance_after=expected_balance_after,
            )

    return TimeAccountResponse(
        employee_id=employee_id,
        current_balance=current_balance,
        history=history,
        projected=projected,
    )
