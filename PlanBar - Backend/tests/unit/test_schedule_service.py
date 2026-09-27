from datetime import date, time
from unittest.mock import patch

import pytest
from app.db.base import Base
from app.db.models.employee import Contract, Employee, Timecard
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.shift_wish import ShiftWish
from app.db.models.team import Team
from app.db.models.user import User
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
    submit_schedule_to_tito,
    update_schedule,
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


def test_create_schedule_derives_week_from_date(db_session):
    """week muss aus dem Datum abgeleitet werden, Client-Werte werden ignoriert."""
    data = ScheduleCreate(
        name="Derived Week",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 14),
        shiftplans=[
            ShiftplanCreate(
                employee_id=1,
                date=date(2026, 6, 1),
                shift_id="früh",
                start_time=time(6, 0),
                end_time=time(14, 0),
                week="B",
            ),
            ShiftplanCreate(
                employee_id=1,
                date=date(2026, 6, 8),
                shift_id="früh",
                start_time=time(6, 0),
                end_time=time(14, 0),
            ),
        ],
    )
    schedule = create_schedule(db_session, data)
    weeks = {sp.date: sp.week for sp in schedule.shiftplans}
    assert weeks[date(2026, 6, 1)] == "A"
    assert weeks[date(2026, 6, 8)] == "B"


def test_create_schedule_scope_rejects_other_parity(db_session):
    """Bei week_type='A' müssen Schichten auf A-Daten liegen."""
    data = ScheduleCreate(
        name="Scoped A",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 14),
        week_type="A",
        shiftplans=[
            ShiftplanCreate(
                employee_id=1,
                date=date(2026, 6, 10),
                shift_id="früh",
                start_time=time(6, 0),
                end_time=time(14, 0),
            ),
        ],
    )
    with pytest.raises(ValueError, match="begrenzt"):
        create_schedule(db_session, data)


def test_replace_all_shifts_derives_week(db_session):
    schedule = create_schedule(
        db_session,
        ScheduleCreate(name="Derive", start_date=date(2026, 6, 1), end_date=date(2026, 6, 14)),
    )
    new_shifts = [
        ShiftplanCreate(
            employee_id=1,
            date=date(2026, 6, 8),
            shift_id="spät",
            start_time=time(14, 0),
            end_time=time(22, 0),
            break_start="18:00",
            break_end="18:30",
            week="A",
        ),
    ]
    replaced, _ = replace_all_shifts(db_session, schedule, new_shifts)
    assert replaced.shiftplans[0].week == "B"


def test_replace_all_shifts_scope_rejects_other_parity(db_session):
    schedule = create_schedule(
        db_session,
        ScheduleCreate(name="Scoped B", start_date=date(2026, 6, 1), end_date=date(2026, 6, 14), week_type="B"),
    )
    new_shifts = [
        ShiftplanCreate(
            employee_id=1,
            date=date(2026, 6, 2),
            shift_id="spät",
            start_time=time(14, 0),
            end_time=time(22, 0),
        ),
    ]
    with pytest.raises(ValueError, match="begrenzt"):
        replace_all_shifts(db_session, schedule, new_shifts)


def test_update_schedule_scope_change_validated(db_session):
    """Scope-Änderung auf 'A' muss fehlschlagen, wenn B-Schichten existieren."""
    schedule = create_schedule(
        db_session,
        ScheduleCreate(
            name="Scope Change",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 14),
            shiftplans=[
                ShiftplanCreate(
                    employee_id=1,
                    date=date(2026, 6, 10),
                    shift_id="früh",
                    start_time=time(6, 0),
                    end_time=time(14, 0),
                ),
            ],
        ),
    )
    with pytest.raises(ValueError, match="unzulässig"):
        update_schedule(db_session, schedule, ScheduleUpdate(week_type="A"))
    assert schedule.week_type is None


def test_wish_week_for_date_encoding(db_session):
    from app.services.schedule_service import wish_week_for_date

    assert wish_week_for_date(date(2026, 6, 1)) == 1
    assert wish_week_for_date(date(2026, 6, 8)) == 2
    assert wish_week_for_date(date(2026, 6, 7)) == 1
    assert wish_week_for_date(date(2026, 6, 14)) == 2


def test_get_schedule_by_id(db_session):
    data = ScheduleCreate(name="Find Me", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7))
    created = create_schedule(db_session, data)
    found = get_schedule_by_id(db_session, created.id)
    assert found is not None
    assert found.name == "Find Me"


def test_get_schedule_by_id_not_found(db_session):
    assert get_schedule_by_id(db_session, 99999) is None


def test_list_schedules(db_session):
    create_schedule(
        db_session,
        ScheduleCreate(name="S1", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7)),
    )
    create_schedule(
        db_session,
        ScheduleCreate(name="S2", start_date=date(2026, 6, 8), end_date=date(2026, 6, 14)),
    )
    schedules = list_schedules(db_session)
    assert len(schedules) >= 2


def test_update_schedule(db_session):
    schedule = create_schedule(
        db_session,
        ScheduleCreate(name="Old", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7)),
    )
    updated = update_schedule(db_session, schedule, ScheduleUpdate(name="New", week_type="A"))
    assert updated.name == "New"
    assert updated.week_type == "A"


def test_delete_schedule(db_session):
    schedule = create_schedule(
        db_session,
        ScheduleCreate(name="Delete Me", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7)),
    )
    sched_id = schedule.id
    delete_schedule(db_session, schedule)
    assert get_schedule_by_id(db_session, sched_id) is None


def test_replace_all_shifts(db_session):
    schedule = create_schedule(
        db_session,
        ScheduleCreate(name="Replace", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7)),
    )
    new_shifts = [
        ShiftplanCreate(
            employee_id=1,
            date=date(2026, 6, 1),
            shift_id="spät",
            start_time=time(14, 0),
            end_time=time(22, 0),
            break_start="18:00",
            break_end="18:30",
        ),
    ]
    replaced, arbzg_result = replace_all_shifts(db_session, schedule, new_shifts)
    assert len(replaced.shiftplans) == 1
    assert replaced.shiftplans[0].shift_id == "spät"
    # Valid single shift should have no violations
    assert arbzg_result.is_valid


def test_get_schedule_summary_with_shifts(db_session):
    data = ScheduleCreate(
        name="Summary",
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
            ShiftplanCreate(
                employee_id=2,
                date=date(2026, 6, 1),
                shift_id="spät",
                start_time=time(14, 0),
                end_time=time(22, 0),
            ),
        ],
    )
    schedule = create_schedule(db_session, data)
    summary = get_schedule_summary(db_session, schedule)
    assert summary["total_shifts"] == 2
    assert summary["total_employees"] == 2
    assert summary["date_range"] is not None


def test_get_schedule_summary_no_shifts(db_session):
    schedule = create_schedule(
        db_session,
        ScheduleCreate(name="Empty", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7)),
    )
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


def test_build_tito_payload_week_type_none(db_session):
    """week_type=None muss alle Daten einschließen (kein Filter)."""
    schedule = Schedule(
        name="Week Type None",
        start_date=date(2026, 6, 1),  # Monday, week A
        end_date=date(2026, 6, 14),  # Sunday, week B
        status="draft",
        week_type=None,
        role_requirements={"früh": "2", "spät": "1"},
    )
    db_session.add(schedule)
    db_session.commit()
    payload = _build_tito_payload(schedule, [], [], db=db_session)
    # 14 days × 2 requirements = 28
    assert len(payload["requirements"]) == 28


def test_build_tito_payload_week_type_a(db_session):
    """week_type='A' muss nur A-Wochen-Daten einschließen."""
    schedule = Schedule(
        name="Week Type A",
        start_date=date(2026, 6, 1),  # Monday, week A
        end_date=date(2026, 6, 14),  # Sunday, week B
        status="draft",
        week_type="A",
        role_requirements={"früh": "2", "spät": "1"},
    )
    db_session.add(schedule)
    db_session.commit()
    payload = _build_tito_payload(schedule, [], [], db=db_session)
    # Only week A dates (June 1-7) = 7 days × 2 = 14
    assert len(payload["requirements"]) == 14
    for req in payload["requirements"]:
        d = date.fromisoformat(req["date"])
        assert date(2026, 6, 1) <= d <= date(2026, 6, 7), f"{d} is not in week A range"


def test_build_tito_payload_week_type_b(db_session):
    """week_type='B' muss nur B-Wochen-Daten einschließen."""
    schedule = Schedule(
        name="Week Type B",
        start_date=date(2026, 6, 1),  # Monday, week A
        end_date=date(2026, 6, 14),  # Sunday, week B
        status="draft",
        week_type="B",
        role_requirements={"früh": "2", "spät": "1"},
    )
    db_session.add(schedule)
    db_session.commit()
    payload = _build_tito_payload(schedule, [], [], db=db_session)
    # Only week B dates (June 8-14) = 7 days × 2 = 14
    assert len(payload["requirements"]) == 14
    for req in payload["requirements"]:
        d = date.fromisoformat(req["date"])
        assert date(2026, 6, 8) <= d <= date(2026, 6, 14), f"{d} is not in week B range"


def test_build_tito_payload_week_type_filters_wishes(db_session):
    """week_type='A' muss auch Wünsche auf B-Daten aus dem Payload ausschließen."""
    schedule = Schedule(
        name="Wish Scope A",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 14),
        status="draft",
        week_type="A",
    )
    db_session.add(schedule)
    db_session.commit()

    wish_a = ShiftWish(employee_id=1, date=date(2026, 6, 3), type="day_off", status="approved")
    wish_b = ShiftWish(employee_id=1, date=date(2026, 6, 10), type="day_off", status="approved")
    db_session.add_all([wish_a, wish_b])
    db_session.commit()

    payload = _build_tito_payload(schedule, [], [wish_a, wish_b], db=db_session)
    wish_dates = [w["date"] for w in payload["wishes"]]
    assert wish_dates == ["2026-06-03"]


def test_build_tito_payload_no_week_type_keeps_all_wishes(db_session):
    """week_type=None darf Wünsche beider Paritäten einschließen."""
    schedule = Schedule(
        name="Wish Scope None",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 14),
        status="draft",
    )
    db_session.add(schedule)
    db_session.commit()

    wish_a = ShiftWish(employee_id=1, date=date(2026, 6, 3), type="day_off", status="approved")
    wish_b = ShiftWish(employee_id=1, date=date(2026, 6, 10), type="day_off", status="approved")
    db_session.add_all([wish_a, wish_b])
    db_session.commit()

    payload = _build_tito_payload(schedule, [], [wish_a, wish_b], db=db_session)
    assert len(payload["wishes"]) == 2


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
    contract = Contract(
        employee_id=employee.id,
        weekly_working_hours=35,
        break_time=45,
        hired_role="supervisor",
    )
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
    schedule = Schedule(
        name="Template Test",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
    )
    db_session.add(schedule)
    db_session.commit()

    sp = Shiftplan(
        schedule_id=schedule.id,
        employee_id=1,
        date=date(2026, 6, 1),
        shift_id="früh",
        start_time=time(6, 0),
        end_time=time(14, 0),
        week=23,
    )
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
            {
                "id": "frueh",
                "name": "Frühschicht",
                "startTime": "06:00",
                "endTime": "14:00",
                "requirements": {"1": 2},
            },
            {
                "id": "spaet",
                "name": "Spätschicht",
                "startTime": "14:00",
                "endTime": "22:00",
                "requirements": {"2": 1},
            },
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
    schedule = Schedule(
        name="Empty Templates",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
    )
    templates = _build_shift_templates(schedule)
    assert templates == []


def test_create_schedule_with_shift_templates(db_session):
    shift_templates = [
        {
            "id": "frueh",
            "name": "Früh",
            "startTime": "06:00",
            "endTime": "14:00",
            "requirements": {"1": 2},
        },
        {
            "id": "spaet",
            "name": "Spät",
            "startTime": "14:00",
            "endTime": "22:00",
            "requirements": {"2": 1},
        },
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


# ─────────────────────────────────────────────────────────────────────
# TiTO team-scope: submit_schedule_to_tito filters employees/wishes
# ─────────────────────────────────────────────────────────────────────


def _make_team_scope_data(db_session):
    """Create shared test data: 2 teams, 4 employees, planer in team_a."""
    team_a = Team(name="TeamA", color="#111111")
    team_b = Team(name="TeamB", color="#222222")
    db_session.add_all([team_a, team_b])
    db_session.commit()

    emp_a1 = Employee(first_name="A1", last_name="Worker")
    emp_a2 = Employee(first_name="A2", last_name="Worker")
    emp_b1 = Employee(first_name="B1", last_name="Worker")
    emp_b2 = Employee(first_name="B2", last_name="Worker")
    db_session.add_all([emp_a1, emp_a2, emp_b1, emp_b2])
    db_session.commit()

    emp_a1.teams.append(team_a)
    emp_a2.teams.append(team_a)
    emp_b1.teams.append(team_b)
    emp_b2.teams.append(team_b)
    db_session.commit()

    planer_user = User(
        username="tito_planer",
        email="tito_planer@test.com",
        password_hash="x",
        role="planer",
    )
    admin = User(
        username="tito_admin",
        email="tito_admin@test.com",
        password_hash="x",
        role="admin",
    )
    db_session.add_all([planer_user, admin])
    db_session.commit()
    db_session.refresh(planer_user)
    db_session.refresh(admin)

    planer_emp = Employee(first_name="Planer", last_name="Emp")
    db_session.add(planer_emp)
    db_session.commit()
    planer_emp.teams.append(team_a)
    planer_emp.user_id = planer_user.id
    db_session.commit()

    schedule = Schedule(
        name="TiTO Team Test",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
        role_requirements={"früh": "1"},
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    wish_a = ShiftWish(
        employee_id=emp_a1.id,
        date=date(2026, 6, 3),
        type="day_off",
        note="A wish",
        status="approved",
    )
    wish_b = ShiftWish(
        employee_id=emp_b1.id,
        date=date(2026, 6, 4),
        type="day_off",
        note="B wish",
        status="approved",
    )
    db_session.add_all([wish_a, wish_b])
    db_session.commit()

    return {
        "teams": (team_a, team_b),
        "employees": (emp_a1, emp_a2, emp_b1, emp_b2),
        "planer": planer_user,
        "admin": admin,
        "schedule": schedule,
    }


@pytest.mark.asyncio
async def test_submit_tito_admin_gets_all_employees(db_session):
    data = _make_team_scope_data(db_session)
    captured = {}

    async def fake_submit(payload):
        captured["payload"] = payload
        return {"jobId": 1}

    with patch("app.services.schedule_service.tito_proxy.submit_job", side_effect=fake_submit):
        result = await submit_schedule_to_tito(db_session, data["schedule"], user=data["admin"])

    emp_ids = {e["id"] for e in captured["payload"]["employees"]}
    assert emp_ids == {"emp_001", "emp_002", "emp_003", "emp_004", "emp_005"}
    assert len(captured["payload"]["wishes"]) == 2
    assert result.status == "submitted"


@pytest.mark.asyncio
async def test_submit_tito_planer_gets_only_own_team_employees(db_session):
    data = _make_team_scope_data(db_session)
    captured = {}

    async def fake_submit(payload):
        captured["payload"] = payload
        return {"jobId": 2}

    with patch("app.services.schedule_service.tito_proxy.submit_job", side_effect=fake_submit):
        result = await submit_schedule_to_tito(db_session, data["schedule"], user=data["planer"])

    emp_ids = {e["id"] for e in captured["payload"]["employees"]}
    assert emp_ids == {"emp_001", "emp_002", "emp_005"}
    assert len(captured["payload"]["wishes"]) == 1
    assert captured["payload"]["wishes"][0]["employeeId"] == "emp_001"
    assert result.status == "submitted"


@pytest.mark.asyncio
async def test_submit_tito_planer_no_team_raises(db_session):
    schedule = Schedule(
        name="No Team",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    planer = User(
        username="unassigned_planer",
        email="unassigned@test.com",
        password_hash="x",
        role="planer",
    )
    db_session.add(planer)
    db_session.commit()
    db_session.refresh(planer)

    with (
        patch("app.services.schedule_service.tito_proxy.submit_job"),
        pytest.raises(ValueError, match="not assigned to any team"),
    ):
        await submit_schedule_to_tito(db_session, schedule, user=planer)


# ─────────────────────────────────────────────────────────────────────
# maxCount / maximizeStaffing features
# ─────────────────────────────────────────────────────────────────────


def test_build_tito_payload_with_maxCount(db_session):
    """shift_templates with maxRequirements must produce requirements with maxCount."""
    schedule = Schedule(
        name="MaxCount Test",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        status="draft",
        shift_templates=[
            {
                "id": "frueh",
                "name": "Frühschicht",
                "startTime": "06:00",
                "endTime": "14:00",
                "requirements": {"1": 2},
                "maxRequirements": {"1": 3},
            },
        ],
    )
    db_session.add(schedule)
    db_session.commit()

    payload = _build_tito_payload(schedule, [], [], db=db_session)
    reqs = payload["requirements"]
    assert len(reqs) == 3
    assert all(r.get("maxCount") == 3 for r in reqs)
    assert all(r["count"] == 2 for r in reqs)


def test_build_tito_payload_without_maxCount(db_session):
    """shift_templates without maxRequirements must not set maxCount."""
    schedule = Schedule(
        name="No MaxCount Test",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        status="draft",
        shift_templates=[
            {
                "id": "frueh",
                "name": "Frühschicht",
                "startTime": "06:00",
                "endTime": "14:00",
                "requirements": {"1": 2},
            },
        ],
    )
    db_session.add(schedule)
    db_session.commit()

    payload = _build_tito_payload(schedule, [], [], db=db_session)
    reqs = payload["requirements"]
    assert len(reqs) == 3
    assert all(r.get("maxCount") is None for r in reqs)


def test_build_tito_payload_maximizeStaffing_in_config(db_session):
    """maximizeStaffing in metadata_json must appear as maximizeStaffing in config."""
    schedule = Schedule(
        name="MaxStaffing On",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
        metadata_json={"maximizeStaffing": True},
    )
    db_session.add(schedule)
    db_session.commit()

    payload = _build_tito_payload(schedule, [], [])
    assert payload["config"]["maximizeStaffing"] is True


def test_build_tito_payload_maximizeStaffing_false_by_default(db_session):
    """maximizeStaffing must default to False when not explicitly set."""
    schedule = Schedule(
        name="MaxStaffing Default",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
    )
    db_session.add(schedule)
    db_session.commit()

    payload = _build_tito_payload(schedule, [], [])
    assert payload["config"]["maximizeStaffing"] is False


@pytest.mark.asyncio
async def test_submit_tito_rejects_non_draft_status(db_session):
    """submit_schedule_to_tito must raise ValueError for non-draft/non-failed schedules."""
    for status in ("submitted", "completed"):
        schedule = Schedule(
            name=f"Status {status}",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 7),
            status=status,
        )
        db_session.add(schedule)
        db_session.commit()
        db_session.refresh(schedule)

        with pytest.raises(ValueError, match="cannot be submitted"):
            await submit_schedule_to_tito(db_session, schedule)


@pytest.mark.asyncio
async def test_submit_tito_allows_draft_status(db_session):
    """submit_schedule_to_tito must proceed for draft schedules."""
    schedule = Schedule(
        name="Draft Schedule",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
        role_requirements={"früh": "1"},
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    async def fake_submit(payload):
        return {"jobId": 1}

    with patch("app.services.schedule_service.tito_proxy.submit_job", side_effect=fake_submit):
        result = await submit_schedule_to_tito(db_session, schedule)

    assert result.status == "submitted"
    assert result.tito_job_id == 1


@pytest.mark.asyncio
async def test_submit_tito_allows_failed_status(db_session):
    """submit_schedule_to_tito must proceed for failed schedules (retry via submit path)."""
    schedule = Schedule(
        name="Failed Schedule",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="failed",
        role_requirements={"früh": "1"},
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    async def fake_submit(payload):
        return {"jobId": 2}

    with patch("app.services.schedule_service.tito_proxy.submit_job", side_effect=fake_submit):
        result = await submit_schedule_to_tito(db_session, schedule)

    assert result.status == "submitted"


# ─────────────────────────────────────────────────────────────────────
# C1: versioned idempotency key + 409 handling
# ─────────────────────────────────────────────────────────────────────


def test_build_tito_payload_idempotency_key_first_attempt(db_session):
    """C1: Erste Submission → deterministischer Key schedule_{id}_1 (kein Zeitstempel)."""
    schedule = Schedule(
        name="Idem 1",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
    )
    db_session.add(schedule)
    db_session.commit()

    payload = _build_tito_payload(schedule, [], [])
    assert payload["metadata"]["idempotency_key"] == f"schedule_{schedule.id}_1"


def test_build_tito_payload_idempotency_key_versioned(db_session):
    """C1: erneute Submission (nach fehlgeschlagenem Callback) → schedule_{id}_2."""
    schedule = Schedule(
        name="Idem 2",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="failed",
        tito_job_id=17,
        metadata_json={"submitAttempt": 1},
    )
    db_session.add(schedule)
    db_session.commit()

    payload = _build_tito_payload(schedule, [], [])
    assert payload["metadata"]["idempotency_key"] == f"schedule_{schedule.id}_2"


@pytest.mark.asyncio
async def test_submit_persists_submit_attempt(db_session):
    """C1: nach erfolgreicher Submission wird submitAttempt persistiert."""
    schedule = Schedule(
        name="Attempt",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
        role_requirements={"früh": "1"},
    )
    db_session.add(schedule)
    db_session.commit()

    async def fake_submit(payload):
        assert payload["metadata"]["idempotency_key"] == f"schedule_{schedule.id}_1"
        return {"jobId": 99}

    with patch("app.services.schedule_service.tito_proxy.submit_job", side_effect=fake_submit):
        result = await submit_schedule_to_tito(db_session, schedule)

    assert result.tito_job_id == 99
    assert result.status == "submitted"
    assert (result.metadata_json or {}).get("submitAttempt") == 1

    # Resubmission after a failed callback uses the versioned key
    result.status = "failed"
    db_session.commit()
    captured = {}

    async def fake_submit_2(payload):
        captured["key"] = payload["metadata"]["idempotency_key"]
        return {"jobId": 100}

    with patch("app.services.schedule_service.tito_proxy.submit_job", side_effect=fake_submit_2):
        await submit_schedule_to_tito(db_session, result)

    assert captured["key"] == f"schedule_{schedule.id}_2"


@pytest.mark.asyncio
async def test_submit_tito_409_raises_clean_value_error(db_session):
    """C1: 409 von TiTO → klarer ValueError (kein 500), Status bleibt unverändert."""
    import httpx

    schedule = Schedule(
        name="Conflict",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
        role_requirements={"früh": "1"},
    )
    db_session.add(schedule)
    db_session.commit()

    request = httpx.Request("POST", "http://tito/jobs")
    response = httpx.Response(409, request=request, json={"detail": "idempotency key already used"})
    exc = httpx.HTTPStatusError("409 Conflict", request=request, response=response)

    with (
        patch("app.services.schedule_service.tito_proxy.submit_job", side_effect=exc),
        pytest.raises(ValueError, match="bereits bei TiTO eingereicht"),
    ):
        await submit_schedule_to_tito(db_session, schedule)

    db_session.refresh(schedule)
    assert schedule.status == "draft"  # nicht auf 'failed' gesetzt


@pytest.mark.asyncio
async def test_submit_tito_409_adopts_job_id_if_present(db_session):
    """C1: liefert TiTO im 409-Body ein jobId, wird es übernommen (Status 'submitted')."""
    import httpx

    schedule = Schedule(
        name="Conflict Adopt",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
        role_requirements={"früh": "1"},
    )
    db_session.add(schedule)
    db_session.commit()

    request = httpx.Request("POST", "http://tito/jobs")
    response = httpx.Response(409, request=request, json={"jobId": 555, "detail": "duplicate"})
    exc = httpx.HTTPStatusError("409 Conflict", request=request, response=response)

    with patch("app.services.schedule_service.tito_proxy.submit_job", side_effect=exc):
        result = await submit_schedule_to_tito(db_session, schedule)

    assert result.status == "submitted"
    assert result.tito_job_id == 555


@pytest.mark.asyncio
async def test_submit_tito_empty_requirements_raises(db_session):
    """C5: Submission ohne Requirements → ValueError (400/422), kein TiTO-Call."""
    schedule = Schedule(
        name="No Reqs",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
    )
    db_session.add(schedule)
    db_session.commit()

    with (
        patch("app.services.schedule_service.tito_proxy.submit_job") as mock_submit,
        pytest.raises(ValueError, match="Requirements"),
    ):
        await submit_schedule_to_tito(db_session, schedule)

    mock_submit.assert_not_called()
    db_session.refresh(schedule)
    assert schedule.status == "draft"


# ─────────────────────────────────────────────────────────────────────
# C2/C3: solver config + state holidays in payload
# ─────────────────────────────────────────────────────────────────────


def test_build_tito_payload_solver_config(db_session):
    """C2: ArbZG-/Solver-Parameter aus den Backend-Settings im config-Abschnitt."""
    schedule = Schedule(
        name="Config Test",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
        role_requirements={"früh": "1"},
    )
    db_session.add(schedule)
    db_session.commit()

    payload = _build_tito_payload(schedule, [], [])
    config = payload["config"]
    assert config["min_rest_time_hours"] == 11
    assert config["max_daily_work_hours"] == 10
    assert config["max_consecutive_days"] == 6
    assert config["min_free_sundays_per_year"] == 15
    assert config["night_window_start"] == "23:00"
    assert config["night_window_end"] == "06:00"
    assert config["night_work_max_hours"] == 10
    assert config["rest_time_shift_workers_hours"] is None
    assert config["max_weekly_hours_law"] == 48


def test_build_tito_payload_holiday_subdivision(db_session, monkeypatch):
    """C3: german_state='BW' → Fronleichnam (2026-06-04) in holidayDates."""
    from app.config import settings

    schedule = Schedule(
        name="BW Holidays",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
        role_requirements={"früh": "1"},
    )
    db_session.add(schedule)
    db_session.commit()

    monkeypatch.setattr(settings, "german_state", None)
    payload = _build_tito_payload(schedule, [], [])
    assert "2026-06-04" not in payload["config"]["holidayDates"]  # nur bundesweit

    monkeypatch.setattr(settings, "german_state", "BW")
    payload = _build_tito_payload(schedule, [], [])
    assert "2026-06-04" in payload["config"]["holidayDates"]  # Fronleichnam in BW


# ─────────────────────────────────────────────────────────────────────
# C4: preShifts + overlap warning + additive timecards
# ─────────────────────────────────────────────────────────────────────


def test_build_tito_payload_pre_shifts(db_session):
    """C4a: bestehende Shiftplans (andere + eigener Draft) als preShifts, ±14-Tage-Fenster."""
    emp = Employee(first_name="Pre", last_name="Shift")
    db_session.add(emp)
    db_session.commit()

    other = Schedule(name="Other", start_date=date(2026, 5, 25), end_date=date(2026, 5, 31), status="completed")
    own = Schedule(name="Own", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7), status="draft")
    db_session.add_all([other, own])
    db_session.commit()

    def _sp(sched_id, d, shift_id):
        return Shiftplan(
            schedule_id=sched_id,
            employee_id=emp.id,
            date=d,
            shift_id=shift_id,
            start_time=time(8, 0),
            end_time=time(16, 0),
        )

    db_session.add_all(
        [
            _sp(other.id, date(2026, 5, 26), "in-window"),  # 6 Tage vor start → enthalten
            _sp(other.id, date(2026, 5, 23), "deep-history"),  # 11 Tage vor start → alt 7-Tage-Fenster, neu enthalten
            _sp(other.id, date(2026, 5, 18), "window-start-boundary"),  # genau start-14 → enthalten
            _sp(other.id, date(2026, 5, 17), "too-old"),  # 15 Tage vor start → draußen
            _sp(other.id, date(2026, 6, 9), "after-end"),  # 2 Tage nach end → neu enthalten
            _sp(other.id, date(2026, 6, 22), "far-future"),  # > end+14 → draußen
            _sp(own.id, date(2026, 6, 2), "own-draft"),  # eigener Draft → enthalten
        ]
    )
    db_session.commit()

    payload = _build_tito_payload(own, [emp], [], db=db_session)
    pre = payload["preShifts"]
    dates = {(p["employeeId"], p["date"], p["startTime"], p["endTime"]) for p in pre}
    assert (f"emp_{emp.id:03d}", "2026-05-26", "08:00", "16:00") in dates
    assert (f"emp_{emp.id:03d}", "2026-05-23", "08:00", "16:00") in dates
    assert (f"emp_{emp.id:03d}", "2026-05-18", "08:00", "16:00") in dates
    assert (f"emp_{emp.id:03d}", "2026-06-09", "08:00", "16:00") in dates
    assert (f"emp_{emp.id:03d}", "2026-06-02", "08:00", "16:00") in dates
    for excluded in ("2026-05-17", "2026-06-22"):
        assert all(p["date"] != excluded for p in pre)
    assert all(p["employeeId"] == f"emp_{emp.id:03d}" for p in pre)


def test_build_tito_payload_pre_shifts_empty_without_db(db_session):
    schedule = Schedule(name="No DB", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7), status="draft")
    db_session.add(schedule)
    db_session.commit()
    payload = _build_tito_payload(schedule, [], [])
    assert payload["preShifts"] == []


def test_create_schedule_overlap_warning(db_session):
    """C4b: überlappender Zeitraum → Warning in Response-Metadaten (kein 422)."""
    first = create_schedule(
        db_session,
        ScheduleCreate(name="First", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7)),
    )
    overlapping = create_schedule(
        db_session,
        ScheduleCreate(name="Second", start_date=date(2026, 6, 5), end_date=date(2026, 6, 12)),
    )
    disjoint = create_schedule(
        db_session,
        ScheduleCreate(name="Third", start_date=date(2026, 6, 15), end_date=date(2026, 6, 21)),
    )

    assert first.metadata_json is None or "overlapWarnings" not in (first.metadata_json or {})
    warnings = (overlapping.metadata_json or {}).get("overlapWarnings", [])
    assert len(warnings) == 1
    assert str(first.id) in warnings[0]
    assert "overlapWarnings" not in (disjoint.metadata_json or {})


# ─────────────────────────────────────────────────────────────────────
# Employee payload extension (ArbZG fields + protectedDaysWorkedYTD)
# ─────────────────────────────────────────────────────────────────────


def test_build_tito_payload_employee_arbzg_fields(db_session):
    from datetime import date as date_cls

    emp = Employee(
        first_name="Minor",
        last_name="Night",
        is_minor=True,
        is_night_worker=True,
        is_shift_worker=True,
        night_worker_exam_date=date_cls(2026, 2, 1),
        protection_until=date_cls(2026, 6, 15),
    )
    db_session.add(emp)
    db_session.commit()

    schedule = Schedule(
        name="Emp ArbZG",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
        role_requirements={"früh": "1"},
    )
    db_session.add(schedule)
    db_session.commit()

    payload = _build_tito_payload(schedule, [emp], [], db=db_session)
    entry = payload["employees"][0]
    assert entry["isMinor"] is True
    assert entry["isNightWorker"] is True
    assert entry["isShiftWorker"] is True
    assert entry["nightWorkerExamDate"] == "2026-02-01"
    assert entry["protectionUntil"] == "2026-06-15"
    assert entry["protectedDaysWorkedYTD"] == 0  # keine Historie


def test_build_tito_payload_protected_days_worked_ytd(db_session):
    """protectedDaysWorkedYTD: Arbeitstage an Sonntagen/Feiertagen des laufenden Jahres bis heute."""
    from datetime import date as date_cls

    emp = Employee(first_name="Sun", last_name="Worker")
    db_session.add(emp)
    db_session.commit()

    other = Schedule(name="Hist", start_date=date(2026, 1, 1), end_date=date(2026, 6, 7), status="completed")
    db_session.add(other)
    db_session.commit()

    def _sp(d):
        return Shiftplan(
            schedule_id=other.id,
            employee_id=emp.id,
            date=d,
            shift_id="x",
            start_time=time(8, 0),
            end_time=time(16, 0),
        )

    # 2026-06-07 ist ein Sonntag im laufenden Jahr (vor heute), 2026-06-03 ein Werktag
    db_session.add_all([_sp(date_cls(2026, 6, 7)), _sp(date_cls(2026, 6, 3))])
    db_session.commit()

    schedule = Schedule(
        name="YTD",
        start_date=date(2026, 9, 7),
        end_date=date(2026, 9, 13),
        status="draft",
        role_requirements={"früh": "1"},
    )
    db_session.add(schedule)
    db_session.commit()

    payload = _build_tito_payload(schedule, [emp], [], db=db_session)
    entry = payload["employees"][0]
    assert entry["protectedDaysWorkedYTD"] == 1


# ─────────────────────────────────────────────────────────────────────
# B5: manual PUT path blocks HARD violations
# ─────────────────────────────────────────────────────────────────────


def test_replace_all_shifts_hard_violation_raises(db_session):
    """B5: HARD-Verstoß im manuellen PUT → ArbZgHardViolationError, nichts geschrieben."""
    from app.services.schedule_service import ArbZgHardViolationError

    emp = Employee(first_name="Hard", last_name="Case")
    db_session.add(emp)
    db_session.commit()

    schedule = create_schedule(
        db_session,
        ScheduleCreate(name="Hard Block", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7)),
    )
    existing = Shiftplan(
        schedule_id=schedule.id,
        employee_id=emp.id,
        date=date(2026, 6, 2),
        shift_id="keep",
        start_time=time(8, 0),
        end_time=time(16, 0),
    )
    db_session.add(existing)
    db_session.commit()

    with pytest.raises(ArbZgHardViolationError):
        replace_all_shifts(
            db_session,
            schedule,
            [
                ShiftplanCreate(
                    employee_id=emp.id,
                    date=date(2026, 6, 3),
                    shift_id="früh",
                    start_time=time(6, 0),
                    end_time=time(18, 0),  # 12h ohne Pause → HARD
                ),
            ],
        )

    # Bestehende Shiftplans bleiben unangetastet
    remaining = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).all()
    assert len(remaining) == 1
    assert remaining[0].shift_id == "keep"


def test_replace_all_shifts_soft_violation_only_warns(db_session):
    """B5: Nur SOFT-Verstöße → übernehmen, als Warnungen im Ergebnis zurückgeben."""
    emp = Employee(first_name="Soft", last_name="Case")
    db_session.add(emp)
    db_session.commit()

    schedule = create_schedule(
        db_session,
        ScheduleCreate(name="Soft Ok", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7)),
    )

    replaced, result = replace_all_shifts(
        db_session,
        schedule,
        [
            ShiftplanCreate(
                employee_id=emp.id,
                date=date(2026, 6, 7),  # Sonntag → sunday_quota SOFT
                shift_id="früh",
                start_time=time(8, 0),
                end_time=time(16, 0),
                break_start="12:00",
                break_end="12:30",
            ),
        ],
    )
    assert len(replaced.shiftplans) == 1
    assert not result.has_hard_violations
    assert any(v.rule == "sunday_quota" for v in result.violations)
