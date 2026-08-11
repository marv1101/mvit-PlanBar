from sqlalchemy.orm import Session

from app.db.models.employee import Contract, Employee, Timecard
from app.db.models.role import Role
from app.db.models.shift_wish import ShiftWish
from app.db.models.team import Team
from app.db.models.user import User
from app.schemas.employee import (
    ContractCreate,
    ContractUpdate,
    EmployeeCreate,
    EmployeeUpdate,
    TimecardCreate,
    TimecardUpdate,
)
from app.services import audit_service


def _set_employee_teams(db: Session, employee: Employee, team_ids: list[int]) -> None:
    """Replace the employee's team memberships with the given set of team ids."""
    current_ids = {t.id for t in employee.teams}
    target_ids = set(team_ids)

    to_add = target_ids - current_ids
    to_remove = current_ids - target_ids

    if to_add:
        teams_to_add = db.query(Team).filter(Team.id.in_(to_add)).all()
        employee.teams.extend(teams_to_add)

    if to_remove:
        employee.teams = [t for t in employee.teams if t.id not in to_remove]


def create_employee(db: Session, data: EmployeeCreate, actor_id: int | None = None) -> Employee:
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
    if data.role_ids:
        roles = db.query(Role).filter(Role.id.in_(data.role_ids)).all()
        employee.roles = roles
    db.add(employee)
    db.flush()
    if data.user_id:
        user = db.query(User).filter(User.id == data.user_id).first()
        if user and user.employee_id != employee.id:
            user.employee_id = employee.id
            db.add(user)
    if data.team_ids:
        _set_employee_teams(db, employee, data.team_ids)
    db.commit()
    db.refresh(employee)
    audit_service.log_create(db, user_id=actor_id, resource_type="employee", resource_id=str(employee.id))
    return employee


def get_employee_by_id(db: Session, employee_id: int) -> Employee | None:
    return db.query(Employee).filter(Employee.id == employee_id).first()


def list_employees(db: Session, offset: int = 0, limit: int | None = None) -> list[Employee]:
    query = db.query(Employee).order_by(Employee.last_name, Employee.first_name)
    if limit is not None:
        query = query.offset(offset).limit(limit)
    return query.all()


def update_employee(db: Session, employee: Employee, data: EmployeeUpdate, actor_id: int | None = None) -> Employee:
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
        if employee.user_id is not None and employee.user_id != data.user_id:
            old_user = db.query(User).filter(User.id == employee.user_id).first()
            if old_user and old_user.employee_id == employee.id:
                old_user.employee_id = None
                db.add(old_user)
        employee.user_id = data.user_id
        if data.user_id:
            new_user = db.query(User).filter(User.id == data.user_id).first()
            if new_user and new_user.employee_id != employee.id:
                new_user.employee_id = employee.id
                db.add(new_user)
    if data.role_ids is not None:
        roles = db.query(Role).filter(Role.id.in_(data.role_ids)).all()
        employee.roles = roles
    if data.team_ids is not None:
        _set_employee_teams(db, employee, data.team_ids)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    audit_service.log_update(db, user_id=actor_id, resource_type="employee", resource_id=str(employee.id))
    return employee


def delete_employee(db: Session, employee: Employee, actor_id: int | None = None) -> None:
    db.query(Contract).filter(Contract.employee_id == employee.id).delete()
    db.query(Timecard).filter(Timecard.employee_id == employee.id).delete()
    db.query(ShiftWish).filter(ShiftWish.employee_id == employee.id).delete()
    db.delete(employee)
    db.commit()
    audit_service.log_delete(db, user_id=actor_id, resource_type="employee", resource_id=str(employee.id))


def create_contract(db: Session, data: ContractCreate, actor_id: int | None = None) -> Contract:
    contract = Contract(
        employee_id=data.employee_id,
        weekly_working_hours=data.weekly_working_hours,
        break_time=data.break_time,
        hired_role=data.hired_role,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    audit_service.log_create(db, user_id=actor_id, resource_type="contract", resource_id=str(contract.id))
    return contract


def get_contract_by_id(db: Session, contract_id: int) -> Contract | None:
    return db.query(Contract).filter(Contract.id == contract_id).first()


def list_contracts(db: Session, offset: int = 0, limit: int | None = None) -> list[Contract]:
    query = db.query(Contract).order_by(Contract.id)
    if limit is not None:
        query = query.offset(offset).limit(limit)
    return query.all()


def update_contract(db: Session, contract: Contract, data: ContractUpdate, actor_id: int | None = None) -> Contract:
    if data.weekly_working_hours is not None:
        contract.weekly_working_hours = data.weekly_working_hours
    if data.break_time is not None:
        contract.break_time = data.break_time
    if data.hired_role is not None:
        contract.hired_role = data.hired_role
    db.add(contract)
    db.commit()
    db.refresh(contract)
    audit_service.log_update(db, user_id=actor_id, resource_type="contract", resource_id=str(contract.id))
    return contract


def create_timecard(db: Session, data: TimecardCreate, actor_id: int | None = None) -> Timecard:
    timecard = Timecard(
        employee_id=data.employee_id,
        week=data.week,
        year=data.year,
        balance=data.balance,
        scheduled_hours=data.scheduled_hours,
        actual_hours=data.actual_hours,
        contract_hours=data.contract_hours,
    )
    db.add(timecard)
    db.commit()
    db.refresh(timecard)
    audit_service.log_create(db, user_id=actor_id, resource_type="timecard", resource_id=str(timecard.id))
    return timecard


def get_timecard_by_id(db: Session, timecard_id: int) -> Timecard | None:
    return db.query(Timecard).filter(Timecard.id == timecard_id).first()


def list_timecards(db: Session, offset: int = 0, limit: int | None = None) -> list[Timecard]:
    query = db.query(Timecard).order_by(Timecard.year.desc(), Timecard.week.desc())
    if limit is not None:
        query = query.offset(offset).limit(limit)
    return query.all()


def update_timecard(db: Session, timecard: Timecard, data: TimecardUpdate, actor_id: int | None = None) -> Timecard:
    if data.week is not None:
        timecard.week = data.week
    if data.year is not None:
        timecard.year = data.year
    if data.balance is not None:
        timecard.balance = data.balance
    if data.scheduled_hours is not None:
        timecard.scheduled_hours = data.scheduled_hours
    if data.actual_hours is not None:
        timecard.actual_hours = data.actual_hours
    if data.contract_hours is not None:
        timecard.contract_hours = data.contract_hours
    db.add(timecard)
    db.commit()
    db.refresh(timecard)
    audit_service.log_update(db, user_id=actor_id, resource_type="timecard", resource_id=str(timecard.id))
    return timecard
