from datetime import date, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.employee import Contract, Employee, Timecard
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.shift_wish import ShiftWish
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ShiftplanCreate
from app.services.schedule_service import (
    _build_shift_templates,
    _build_tito_payload,
    create_schedule,
    delete_schedule,
    get_schedule_by_id,
    get_schedule_summary,
    list_schedules,
    replace_all_shifts,
    update_schedule,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


def test_create_schedule_minimal(db_session):
    data = ScheduleCreate(
        name="Test Schedule",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
    )
    schedule = create_schedule(db_session, data)
    assert schedule.name == "Test Schedule"
    assert schedule.status == "draft"
    assert schedule.id is not None


def test_create_schedule_with_shiftplans(db_session):
    data = ScheduleCreate(
        name="With Shifts",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        shiftplans=[
            ShiftplanCreate(
                employee_id=1,
                date=date(2026, 6, 1),
                shift_id="früh",
                start_time=time(6, 0),
                end_time=time(14, 0),
            ),
        ],
    )
    schedule = create_schedule(db_session, data)
    assert len(schedule.shiftplans) == 1


def test_get_schedule_by_id(db_session):
    data = ScheduleCreate(name="Find Me", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7))
    created = create_schedule(db_session, data)
    found = get_schedule_by_id(db_session, created.id)
    assert found is not None
    assert found.name == "Find Me"


def test_get_schedule_by_id_not_found(db_session):
    assert get_schedule_by_id(db_session, 99999) is None


def test_list_schedules(db_session):
    create_schedule(db_session, ScheduleCreate(name="S1", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7)))
    create_schedule(db_session, ScheduleCreate(name="S2", start_date=date(2026, 6, 8), end_date=date(2026, 6, 14)))
    schedules = list_schedules(db_session)
    assert len(schedules) >= 2


def test_update_schedule(db_session):
    schedule = create_schedule(db_session, ScheduleCreate(name="Old", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7)))
    updated = update_schedule(db_session, schedule, ScheduleUpdate(name="New", week_type="A"))
    assert updated.name == "New"
    assert updated.week_type == "A"


def test_delete_schedule(db_session):
    schedule = create_schedule(db_session, ScheduleCreate(name="Delete Me", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7)))
    sched_id = schedule.id
    delete_schedule(db_session, schedule)
    assert get_schedule_by_id(db_session, sched_id) is None


def test_replace_all_shifts(db_session):
    schedule = create_schedule(db_session, ScheduleCreate(name="Replace", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7)))
    new_shifts = [
        ShiftplanCreate(
            employee_id=1,
            date=date(2026, 6, 1),
            shift_id="spät",
            start_time=time(14, 0),
            end_time=time(22, 0),
        ),
    ]
    replaced = replace_all_shifts(db_session, schedule, new_shifts)
    assert len(replaced.shiftplans) == 1
    assert replaced.shiftplans[0].shift_id == "spät"


def test_get_schedule_summary_with_shifts(db_session):
    data = ScheduleCreate(
        name="Summary",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        shiftplans=[
            ShiftplanCreate(employee_id=1, date=date(2026, 6, 1), shift_id="früh", start_time=time(6, 0), end_time=time(14, 0)),
            ShiftplanCreate(employee_id=2, date=date(2026, 6, 1), shift_id="spät", start_time=time(14, 0), end_time=time(22, 0)),
        ],
    )
    schedule = create_schedule(db_session, data)
    summary = get_schedule_summary(db_session, schedule)
    assert summary["total_shifts"] == 2
    assert summary["total_employees"] == 2
    assert summary["date_range"] is not None


def test_get_schedule_summary_no_shifts(db_session):
    schedule = create_schedule(db_session, ScheduleCreate(name="Empty", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7)))
    summary = get_schedule_summary(db_session, schedule)
    assert summary["total_shifts"] == 0
    assert summary["date_range"] is None


def test_build_tito_payload_no_start_date_raises(db_session):
    schedule = Schedule(name="No Date", status="draft")
    db_session.add(schedule)
    db_session.commit()
    with pytest.raises(ValueError, match="must have start_date and end_date"):
        _build_tito_payload(schedule, [], [])


def test_build_tito_payload_minimal(db_session):
    schedule = Schedule(
        name="Minimal",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
    )
    db_session.add(schedule)
    db_session.commit()
    payload = _build_tito_payload(schedule, [], [])
    assert payload["config"]["startDate"] == "2026-06-01"
    assert payload["config"]["endDate"] == "2026-06-07"
    assert payload["employees"] == []
    assert payload["wishes"] == []
    assert len(payload["shiftTemplates"]) == 0


def test_build_tito_payload_with_employees(db_session):
    schedule = Schedule(
        name="With Employees",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
    )
    db_session.add(schedule)
    db_session.commit()

    employee = Employee(first_name="John", last_name="Doe", max_work_hours=8)
    db_session.add(employee)
    db_session.commit()

    payload = _build_tito_payload(schedule, [employee], [])
    assert len(payload["employees"]) == 1
    assert payload["employees"][0]["maxDailyHours"] == 8


def test_build_tito_payload_with_contract(db_session):
    schedule = Schedule(
        name="With Contract",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
    )
    db_session.add(schedule)
    db_session.commit()

    employee = Employee(first_name="Jane", last_name="Smith")
    db_session.add(employee)
    db_session.commit()
    contract = Contract(employee_id=employee.id, weekly_working_hours=35, break_time=45, hired_role="supervisor")
    db_session.add(contract)
    db_session.commit()

    payload = _build_tito_payload(schedule, [employee], [])
    emp = payload["employees"][0]
    assert emp["contractHours"] == 35
    assert emp["breakMinutes"] == 45
    assert emp["role"] == "supervisor"


def test_build_tito_payload_with_wishes(db_session):
    schedule = Schedule(
        name="With Wishes",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
    )
    db_session.add(schedule)
    db_session.commit()

    wish = ShiftWish(employee_id=1, date=date(2026, 6, 3), type="day_off", note="Urlaub")
    db_session.add(wish)
    db_session.commit()

    payload = _build_tito_payload(schedule, [], [wish])
    assert len(payload["wishes"]) == 1
    assert payload["wishes"][0]["employeeId"] == "emp_001"
    assert payload["wishes"][0]["comment"] == "Urlaub"


def test_build_tito_payload_with_requirements(db_session):
    schedule = Schedule(
        name="With Requirements",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        status="draft",
        role_requirements={"früh": "2", "spät": "1"},
    )
    db_session.add(schedule)
    db_session.commit()

    payload = _build_tito_payload(schedule, [], [])
    assert len(payload["requirements"]) == 6
    assert len(payload["shiftTemplates"]) == 2


def test_build_tito_payload_with_current_balance_hours(db_session):
    schedule = Schedule(
        name="Balance Test",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
    )
    db_session.add(schedule)
    db_session.commit()

    employee = Employee(first_name="Balance", last_name="Test")
    db_session.add(employee)
    db_session.commit()

    contract = Contract(employee_id=employee.id, weekly_working_hours=40, break_time=30)
    db_session.add(contract)

    timecard = Timecard(employee_id=employee.id, week=22, year=2026, balance=12.5)
    db_session.add(timecard)
    timecard_old = Timecard(employee_id=employee.id, week=21, year=2026, balance=10.0)
    db_session.add(timecard_old)
    db_session.commit()

    payload = _build_tito_payload(schedule, [employee], [], db=db_session)
    emp = payload["employees"][0]
    assert emp["currentBalanceHours"] == 12.5


def test_build_tito_payload_with_no_timecard_defaults_zero(db_session):
    schedule = Schedule(
        name="No Balance",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
    )
    db_session.add(schedule)
    db_session.commit()

    employee = Employee(first_name="No", last_name="Balance")
    db_session.add(employee)
    db_session.commit()

    payload = _build_tito_payload(schedule, [employee], [], db=db_session)
    emp = payload["employees"][0]
    assert emp.get("currentBalanceHours", 0.0) == 0.0


def test_build_tito_payload_with_callback_url(db_session):
    schedule = Schedule(
        name="Callback Test",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
    )
    db_session.add(schedule)
    db_session.commit()

    payload = _build_tito_payload(schedule, [], [], callback_url="http://custom.example.com")
    assert "custom.example.com" in payload["metadata"]["callback_url"]


def test_build_shift_templates_from_shiftplans(db_session):
    schedule = Schedule(name="Template Test", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7), status="draft")
    db_session.add(schedule)
    db_session.commit()

    sp = Shiftplan(schedule_id=schedule.id, employee_id=1, date=date(2026, 6, 1), shift_id="früh", start_time=time(6, 0), end_time=time(14, 0), week=23)
    db_session.add(sp)
    db_session.commit()
    db_session.refresh(schedule)

    templates = _build_shift_templates(schedule)
    assert len(templates) == 1
    assert templates[0]["id"] == "früh"


def test_build_shift_templates_from_role_requirements(db_session):
    schedule = Schedule(
        name="Role Templates",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
        role_requirements={"früh": "1", "nacht": "1", "unknown": "1"},
    )
    templates = _build_shift_templates(schedule)
    assert len(templates) == 3
    früh = next(t for t in templates if t["id"] == "früh")
    assert früh["startTime"] == "06:00"
    nacht = next(t for t in templates if t["id"] == "nacht")
    assert nacht["startTime"] == "22:00"
    unknown = next(t for t in templates if t["id"] == "unknown")
    assert unknown["startTime"] == "08:00"


def test_build_shift_templates_from_schedule_shift_templates(db_session):
    schedule = Schedule(
        name="Shift Templates Test",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
        shift_templates=[
            {"id": "frueh", "name": "Frühschicht", "startTime": "06:00", "endTime": "14:00", "requirements": {"1": 2}},
            {"id": "spaet", "name": "Spätschicht", "startTime": "14:00", "endTime": "22:00", "requirements": {"2": 1}},
        ],
    )
    templates = _build_shift_templates(schedule)
    assert len(templates) == 2
    frueh = next(t for t in templates if t["id"] == "frueh")
    assert frueh["startTime"] == "06:00"
    assert frueh["endTime"] == "14:00"
    spaet = next(t for t in templates if t["id"] == "spaet")
    assert spaet["startTime"] == "14:00"
    assert spaet["endTime"] == "22:00"


def test_build_tito_payload_with_shift_templates_and_skills(db_session):
    from app.db.models.role import Role
    role_apo = Role(name="Apotheker", color="#ff0000")
    role_pta = Role(name="PTA", color="#00ff00")
    db_session.add_all([role_apo, role_pta])
    db_session.commit()

    schedule = Schedule(
        name="Skills Test",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        status="draft",
        shift_templates=[
            {
                "id": "frueh",
                "name": "Frühschicht",
                "startTime": "06:00",
                "endTime": "14:00",
                "requirements": {"1": 2, "2": 1},
            },
        ],
    )
    db_session.add(schedule)
    db_session.commit()

    payload = _build_tito_payload(schedule, [], [], db=db_session)

    assert len(payload["shiftTemplates"]) == 1
    assert payload["shiftTemplates"][0]["startTime"] == "06:00"
    assert payload["shiftTemplates"][0]["endTime"] == "14:00"

    reqs = payload["requirements"]
    assert len(reqs) == 6

    apo_reqs = [r for r in reqs if r.get("skills") == ["Apotheker"]]
    pta_reqs = [r for r in reqs if r.get("skills") == ["PTA"]]
    assert len(apo_reqs) == 3
    assert all(r["count"] == 2 for r in apo_reqs)
    assert len(pta_reqs) == 3
    assert all(r["count"] == 1 for r in pta_reqs)

    assert all(r["shiftTemplateId"] == "frueh" for r in reqs)


def test_build_tito_payload_employee_skills(db_session):
    from app.db.models.role import Role
    role = Role(name="Apotheker", color="#ff0000")
    db_session.add(role)
    db_session.commit()

    employee = Employee(first_name="John", last_name="Doe")
    employee.roles = [role]
    db_session.add(employee)
    db_session.commit()

    schedule = Schedule(
        name="Emp Skills Test",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        status="draft",
    )
    db_session.add(schedule)
    db_session.commit()

    payload = _build_tito_payload(schedule, [employee], [], db=db_session)
    assert len(payload["employees"]) == 1
    assert payload["employees"][0]["skills"] == ["Apotheker"]


def test_build_tito_payload_backward_compat_role_requirements(db_session):
    """Alter role_requirements-Pfad muss weiterhin funktionieren (ohne skills)."""
    schedule = Schedule(
        name="Backward Compat",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        status="draft",
        role_requirements={"früh": "2", "spät": "1"},
    )
    db_session.add(schedule)
    db_session.commit()

    payload = _build_tito_payload(schedule, [], [], db=db_session)
    assert len(payload["requirements"]) == 6
    assert all("skills" not in r for r in payload["requirements"])
    assert payload["shiftTemplates"][0]["startTime"] == "06:00"
    assert payload["shiftTemplates"][1]["startTime"] == "14:00"


def test_build_shift_templates_empty(db_session):
    schedule = Schedule(name="Empty Templates", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7), status="draft")
    templates = _build_shift_templates(schedule)
    assert templates == []


def test_create_schedule_with_shift_templates(db_session):
    shift_templates = [
        {"id": "frueh", "name": "Früh", "startTime": "06:00", "endTime": "14:00", "requirements": {"1": 2}},
        {"id": "spaet", "name": "Spät", "startTime": "14:00", "endTime": "22:00", "requirements": {"2": 1}},
    ]
    data = ScheduleCreate(
        name="With Shift Templates",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        shift_templates=shift_templates,
    )
    schedule = create_schedule(db_session, data)
    assert schedule.shift_templates == shift_templates
    assert len(schedule.shift_templates) == 2
