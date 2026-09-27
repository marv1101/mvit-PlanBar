import pytest
from app.db.base import Base
from app.db.models.role import Role
from app.schemas.employee import (
    ContractCreate,
    ContractUpdate,
    EmployeeCreate,
    EmployeeUpdate,
    TimecardCreate,
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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


def test_create_employee(db_session):
    data = EmployeeCreate(first_name="John", last_name="Doe")
    emp = create_employee(db_session, data)
    assert emp.first_name == "John"
    assert emp.last_name == "Doe"
    assert emp.id is not None


def test_create_employee_with_role_ids(db_session):
    role = Role(name="supervisor", color="#FF0000")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    data = EmployeeCreate(first_name="Jane", last_name="Smith", role_ids=[role.id])
    emp = create_employee(db_session, data)
    assert len(emp.roles) == 1
    assert emp.roles[0].name == "supervisor"


def test_get_employee_by_id_found(db_session):
    emp = create_employee(db_session, EmployeeCreate(first_name="Find", last_name="Me"))
    found = get_employee_by_id(db_session, emp.id)
    assert found is not None
    assert found.first_name == "Find"


def test_get_employee_by_id_not_found(db_session):
    assert get_employee_by_id(db_session, 99999) is None


def test_list_employees(db_session):
    create_employee(db_session, EmployeeCreate(first_name="A", last_name="B"))
    create_employee(db_session, EmployeeCreate(first_name="C", last_name="D"))
    emps = list_employees(db_session)
    assert len(emps) >= 2


def test_update_employee_all_fields(db_session):
    emp = create_employee(db_session, EmployeeCreate(first_name="Old", last_name="Name"))
    updated = update_employee(
        db_session,
        emp,
        EmployeeUpdate(
            first_name="New",
            last_name="Name2",
            email="new@example.com",
            color="#00FF00",
            max_work_hours=8,
        ),
    )
    assert updated.first_name == "New"
    assert updated.last_name == "Name2"
    assert updated.email == "new@example.com"
    assert updated.color == "#00FF00"
    assert updated.max_work_hours == 8


def test_update_employee_partial(db_session):
    emp = create_employee(db_session, EmployeeCreate(first_name="Partial", last_name="Update"))
    updated = update_employee(db_session, emp, EmployeeUpdate(first_name="Changed"))
    assert updated.first_name == "Changed"
    assert updated.last_name == "Update"


def test_create_employee_syncs_user_employee_id(db_session):
    from app.db.models.user import User

    user = User(username="empuser1", email="empuser1@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    emp = create_employee(db_session, EmployeeCreate(first_name="Sync", last_name="Create", user_id=user.id))
    db_session.refresh(user)

    assert emp.user_id == user.id
    assert user.employee_id == emp.id


def test_update_employee_syncs_user_employee_id(db_session):
    from app.db.models.user import User

    user = User(username="empuser2", email="empuser2@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    emp = create_employee(db_session, EmployeeCreate(first_name="Sync", last_name="Update"))
    updated = update_employee(db_session, emp, EmployeeUpdate(user_id=user.id))
    db_session.refresh(user)

    assert updated.user_id == user.id
    assert user.employee_id == emp.id


def test_update_employee_switching_user_unlinks_old(db_session):
    from app.db.models.user import User

    user_a = User(username="empuserA", email="empuserA@example.com", password_hash="x")
    user_b = User(username="empuserB", email="empuserB@example.com", password_hash="x")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    emp = create_employee(db_session, EmployeeCreate(first_name="Switch", last_name="User"))
    update_employee(db_session, emp, EmployeeUpdate(user_id=user_a.id))
    db_session.refresh(user_a)
    assert user_a.employee_id == emp.id

    update_employee(db_session, emp, EmployeeUpdate(user_id=user_b.id))
    db_session.refresh(user_a)
    db_session.refresh(user_b)
    assert user_a.employee_id is None
    assert user_b.employee_id == emp.id


def test_delete_employee_cascades(db_session):
    emp = create_employee(db_session, EmployeeCreate(first_name="Del", last_name="Ete"))
    contract = create_contract(
        db_session,
        ContractCreate(employee_id=emp.id, weekly_working_hours=40, break_time=30),
    )
    timecard = create_timecard(db_session, TimecardCreate(employee_id=emp.id, week=20, year=2026, balance=0))

    delete_employee(db_session, emp)

    assert get_employee_by_id(db_session, emp.id) is None
    assert get_contract_by_id(db_session, contract.id) is None
    assert get_timecard_by_id(db_session, timecard.id) is None


def test_create_contract(db_session):
    emp = create_employee(db_session, EmployeeCreate(first_name="Contract", last_name="Test"))
    data = ContractCreate(employee_id=emp.id, weekly_working_hours=35, break_time=45)
    contract = create_contract(db_session, data)
    assert contract.weekly_working_hours == 35
    assert contract.break_time == 45


def test_get_contract_by_id_not_found(db_session):
    assert get_contract_by_id(db_session, 99999) is None


def test_list_contracts(db_session):
    emp = create_employee(db_session, EmployeeCreate(first_name="CList", last_name="Test"))
    create_contract(
        db_session,
        ContractCreate(employee_id=emp.id, weekly_working_hours=40, break_time=30),
    )
    contracts = list_contracts(db_session)
    assert len(contracts) >= 1


def test_update_contract(db_session):
    emp = create_employee(db_session, EmployeeCreate(first_name="CUpd", last_name="Test"))
    contract = create_contract(
        db_session,
        ContractCreate(employee_id=emp.id, weekly_working_hours=40, break_time=30),
    )
    updated = update_contract(
        db_session,
        contract,
        ContractUpdate(weekly_working_hours=35, break_time=25, hired_role="supervisor"),
    )
    assert updated.weekly_working_hours == 35
    assert updated.break_time == 25
    assert updated.hired_role == "supervisor"


def test_create_timecard(db_session):
    emp = create_employee(db_session, EmployeeCreate(first_name="TCard", last_name="Test"))
    data = TimecardCreate(employee_id=emp.id, week=22, year=2026, balance=5.5)
    tc = create_timecard(db_session, data)
    assert tc.week == 22
    assert tc.year == 2026
    assert tc.balance == 5.5
    assert tc.scheduled_hours == 0.0
    assert tc.actual_hours == 0.0
    assert tc.contract_hours == 0.0


def test_create_timecard_with_extended_fields(db_session):
    emp = create_employee(db_session, EmployeeCreate(first_name="TCExt", last_name="Test"))
    data = TimecardCreate(
        employee_id=emp.id,
        week=23,
        year=2026,
        balance=5.5,
        scheduled_hours=38.0,
        actual_hours=36.0,
        contract_hours=40.0,
    )
    tc = create_timecard(db_session, data)
    assert tc.scheduled_hours == 38.0
    assert tc.actual_hours == 36.0
    assert tc.contract_hours == 40.0
    assert tc.balance == 5.5


def test_timecard_unique_employee_week_year(db_session):
    emp = create_employee(db_session, EmployeeCreate(first_name="TCUniq", last_name="Test"))
    create_timecard(db_session, TimecardCreate(employee_id=emp.id, week=25, year=2026, balance=0))
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        create_timecard(
            db_session,
            TimecardCreate(employee_id=emp.id, week=25, year=2026, balance=5.0),
        )


def test_get_timecard_by_id_not_found(db_session):
    assert get_timecard_by_id(db_session, 99999) is None


def test_list_timecards(db_session):
    emp = create_employee(db_session, EmployeeCreate(first_name="TCList", last_name="Test"))
    create_timecard(db_session, TimecardCreate(employee_id=emp.id, week=20, year=2026, balance=0))
    tcs = list_timecards(db_session)
    assert len(tcs) >= 1


def test_update_timecard(db_session):
    emp = create_employee(db_session, EmployeeCreate(first_name="TCUpd", last_name="Test"))
    tc = create_timecard(db_session, TimecardCreate(employee_id=emp.id, week=20, year=2026, balance=0))
    updated = update_timecard(
        db_session,
        tc,
        TimecardUpdate(week=21, year=2026, balance=10.0, scheduled_hours=35.0),
    )
    assert updated.week == 21
    assert updated.balance == 10.0
    assert updated.scheduled_hours == 35.0


# --- ArbZG-relevant employee fields ---


def test_create_employee_with_arbzg_fields(db_session):
    from datetime import date

    data = EmployeeCreate(
        first_name="Mia",
        last_name="Minor",
        is_minor=True,
        is_night_worker=True,
        is_shift_worker=True,
        night_worker_exam_date=date(2026, 2, 1),
        protection_until=date(2026, 6, 30),
    )
    emp = create_employee(db_session, data)
    assert emp.is_minor is True
    assert emp.is_night_worker is True
    assert emp.is_shift_worker is True
    assert emp.night_worker_exam_date == date(2026, 2, 1)
    assert emp.protection_until == date(2026, 6, 30)


def test_create_employee_arbzg_defaults(db_session):
    emp = create_employee(db_session, EmployeeCreate(first_name="Def", last_name="Arbzg"))
    assert emp.is_minor is False
    assert emp.is_night_worker is False
    assert emp.is_shift_worker is False
    assert emp.night_worker_exam_date is None
    assert emp.protection_until is None


def test_update_employee_arbzg_fields(db_session):
    from datetime import date

    emp = create_employee(db_session, EmployeeCreate(first_name="Upd", last_name="Arbzg"))
    updated = update_employee(
        db_session,
        emp,
        EmployeeUpdate(
            is_minor=True,
            protection_until=date(2026, 6, 30),
        ),
    )
    assert updated.is_minor is True
    assert updated.protection_until == date(2026, 6, 30)

    updated = update_employee(db_session, emp, EmployeeUpdate(is_minor=False))
    assert updated.is_minor is False
    assert updated.protection_until == date(2026, 6, 30)  # unverändert
