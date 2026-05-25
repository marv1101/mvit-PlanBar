from sqlalchemy.orm import Session

from app.db.models.employee import Contract, Employee, Timecard
from app.db.models.shift_wish import ShiftWish
from app.schemas.employee import (
    ContractCreate,
    ContractUpdate,
    EmployeeCreate,
    EmployeeUpdate,
    TimecardCreate,
    TimecardUpdate,
)


def create_employee(db: Session, data: EmployeeCreate) -> Employee:
    employee = Employee(
        user_id=data.user_id,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        color=data.color,
        working_hours_json=data.working_hours_json,
        break_start=data.break_start,
        break_end=data.break_end,
        max_work_hours=data.max_work_hours,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def get_employee_by_id(db: Session, employee_id: int) -> Employee | None:
    return db.query(Employee).filter(Employee.id == employee_id).first()


def list_employees(db: Session) -> list[Employee]:
    return db.query(Employee).order_by(Employee.last_name, Employee.first_name).all()


def update_employee(db: Session, employee: Employee, data: EmployeeUpdate) -> Employee:
    if data.first_name is not None:
        employee.first_name = data.first_name
    if data.last_name is not None:
        employee.last_name = data.last_name
    if data.email is not None:
        employee.email = data.email
    if data.color is not None:
        employee.color = data.color
    if data.working_hours_json is not None:
        employee.working_hours_json = data.working_hours_json
    if data.break_start is not None:
        employee.break_start = data.break_start
    if data.break_end is not None:
        employee.break_end = data.break_end
    if data.max_work_hours is not None:
        employee.max_work_hours = data.max_work_hours
    if data.user_id is not None:
        employee.user_id = data.user_id
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def delete_employee(db: Session, employee: Employee) -> None:
    db.query(Contract).filter(Contract.employee_id == employee.id).delete()
    db.query(Timecard).filter(Timecard.employee_id == employee.id).delete()
    db.query(ShiftWish).filter(ShiftWish.employee_id == employee.id).delete()
    db.delete(employee)
    db.commit()


def create_contract(db: Session, data: ContractCreate) -> Contract:
    contract = Contract(
        employee_id=data.employee_id,
        weekly_working_hours=data.weekly_working_hours,
        break_time=data.break_time,
        hired_role=data.hired_role,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


def get_contract_by_id(db: Session, contract_id: int) -> Contract | None:
    return db.query(Contract).filter(Contract.id == contract_id).first()


def list_contracts(db: Session) -> list[Contract]:
    return db.query(Contract).order_by(Contract.id).all()


def update_contract(db: Session, contract: Contract, data: ContractUpdate) -> Contract:
    if data.weekly_working_hours is not None:
        contract.weekly_working_hours = data.weekly_working_hours
    if data.break_time is not None:
        contract.break_time = data.break_time
    if data.hired_role is not None:
        contract.hired_role = data.hired_role
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


def create_timecard(db: Session, data: TimecardCreate) -> Timecard:
    timecard = Timecard(
        employee_id=data.employee_id,
        week=data.week,
        year=data.year,
        balance=data.balance,
    )
    db.add(timecard)
    db.commit()
    db.refresh(timecard)
    return timecard


def get_timecard_by_id(db: Session, timecard_id: int) -> Timecard | None:
    return db.query(Timecard).filter(Timecard.id == timecard_id).first()


def list_timecards(db: Session) -> list[Timecard]:
    return db.query(Timecard).order_by(Timecard.year.desc(), Timecard.week.desc()).all()


def update_timecard(db: Session, timecard: Timecard, data: TimecardUpdate) -> Timecard:
    if data.week is not None:
        timecard.week = data.week
    if data.year is not None:
        timecard.year = data.year
    if data.balance is not None:
        timecard.balance = data.balance
    db.add(timecard)
    db.commit()
    db.refresh(timecard)
    return timecard
