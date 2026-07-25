"""Tests for team-based schedule filtering and write-access assertions."""

from datetime import date, time

from app.db.models.employee import Employee
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.user import User
from app.schemas.schedule import ShiftplanCreate
from app.schemas.team import TeamCreate
from app.services import schedule_service, team_service


def _make_schedule_with_shift(db_session, name, employee_ids):
    schedule = Schedule(name=name, status="draft")
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)
    for eid in employee_ids:
        sp = Shiftplan(
            schedule_id=schedule.id,
            employee_id=eid,
            date=date(2026, 7, 1),
            shift_id="frueh",
            start_time=time(6, 0),
            end_time=time(14, 0),
            week="A",
        )
        db_session.add(sp)
    db_session.commit()
    db_session.refresh(schedule)
    return schedule


def _employee_with_user_team(db_session, role="planer", team=None):
    emp = Employee(first_name="x", last_name="y")
    db_session.add(emp)
    db_session.commit()
    if team:
        emp.teams.append(team)
        db_session.commit()
    user = User(
        username=f"u-{emp.id}",
        email=f"u-{emp.id}@example.com",
        password_hash="x",
        role=role,
        employee_id=emp.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user, emp


def test_list_schedules_for_admin_returns_all(db_session):
    user, _ = _employee_with_user_team(db_session, role="admin")
    emp1 = Employee(first_name="A", last_name="B")
    emp2 = Employee(first_name="C", last_name="D")
    db_session.add_all([emp1, emp2])
    db_session.commit()

    s1 = _make_schedule_with_shift(db_session, "S1", [emp1.id])
    s2 = _make_schedule_with_shift(db_session, "S2", [emp2.id])

    schedules = schedule_service.list_schedules_for(db_session, user)
    ids = {s.id for s in schedules}
    assert {s1.id, s2.id}.issubset(ids)


def test_list_schedules_for_planer_returns_only_team_schedules(db_session):
    team = team_service.create_team(db_session, TeamCreate(name="FilterTeam"))
    user, emp = _employee_with_user_team(db_session, role="planer", team=team)

    emp_other_team = Employee(first_name="Other", last_name="Employee")
    db_session.add(emp_other_team)
    db_session.commit()

    in_team_schedule = _make_schedule_with_shift(db_session, "InTeam", [emp.id])
    other_schedule = _make_schedule_with_shift(db_session, "OutOfTeam", [emp_other_team.id])
    mixed_schedule = _make_schedule_with_shift(db_session, "Mixed", [emp.id, emp_other_team.id])

    schedules = schedule_service.list_schedules_for(db_session, user)
    ids = {s.id for s in schedules}
    assert in_team_schedule.id in ids
    # Schedule with only foreign employees must not be visible to planer
    assert other_schedule.id not in ids
    # Mixed schedules (planer sees their employees in it) should still be returned
    assert mixed_schedule.id in ids


def test_assert_team_write_access_planer_allowed_for_own_team(db_session):
    team = team_service.create_team(db_session, TeamCreate(name="WriteTeam"))
    user, emp = _employee_with_user_team(db_session, role="planer", team=team)
    schedule = _make_schedule_with_shift(db_session, "Sched", [emp.id])

    # Should not raise
    schedule_service.assert_team_write_access(db_session, schedule, user)


def test_assert_team_write_access_planer_forbidden_for_foreign_employee(db_session):
    team = team_service.create_team(db_session, TeamCreate(name="WriteTeam2"))
    user, _ = _employee_with_user_team(db_session, role="planer", team=team)
    foreign = Employee(first_name="F", last_name="F")
    db_session.add(foreign)
    db_session.commit()
    schedule = _make_schedule_with_shift(db_session, "ForeignSched", [foreign.id])

    try:
        schedule_service.assert_team_write_access(db_session, schedule, user)
        raise AssertionError("expected permission error")
    except PermissionError:
        pass


def test_assert_team_write_access_admin_always_allowed(db_session):
    user, _ = _employee_with_user_team(db_session, role="admin")
    foreign = Employee(first_name="F", last_name="F")
    db_session.add(foreign)
    db_session.commit()
    schedule = _make_schedule_with_shift(db_session, "AdminSched", [foreign.id])

    schedule_service.assert_team_write_access(db_session, schedule, user)


def test_assert_team_write_on_shiftplan_collection_planer(db_session):
    """When creating a schedule with shiftplans, the planner must only reference own team employees."""
    team = team_service.create_team(db_session, TeamCreate(name="CollTeam"))
    user, emp = _employee_with_user_team(db_session, role="planer", team=team)
    foreign = Employee(first_name="FF", last_name="FF")
    db_session.add(foreign)
    db_session.commit()

    own_shiftplan = ShiftplanCreate(
        employee_id=emp.id,
        date=date(2026, 7, 1),
        shift_id="frueh",
        start_time=time(6, 0),
        end_time=time(14, 0),
    )
    foreign_shiftplan = ShiftplanCreate(
        employee_id=foreign.id,
        date=date(2026, 7, 1),
        shift_id="frueh",
        start_time=time(6, 0),
        end_time=time(14, 0),
    )

    # Should not raise for own team only
    schedule_service.assert_team_write_on_shiftplans(db_session, [own_shiftplan], user)

    try:
        schedule_service.assert_team_write_on_shiftplans(db_session, [foreign_shiftplan], user)
        raise AssertionError("expected permission error")
    except PermissionError:
        pass


def test_get_schedule_for_user_planer_403_on_foreign_schedule(db_session):

    team = team_service.create_team(db_session, TeamCreate(name="Own403"))
    user, _ = _employee_with_user_team(db_session, role="planer", team=team)
    foreign = Employee(first_name="F403", last_name="F403")
    db_session.add(foreign)
    db_session.commit()
    schedule = _make_schedule_with_shift(db_session, "Foreign403", [foreign.id])

    try:
        schedule_service.get_schedule_for_user(db_session, schedule.id, user)
        raise AssertionError("expected PermissionError")
    except PermissionError:
        pass


def test_get_schedule_for_user_admin_returns_any(db_session):
    user, _ = _employee_with_user_team(db_session, role="admin")
    foreign = Employee(first_name="Z", last_name="Z")
    db_session.add(foreign)
    db_session.commit()
    schedule = _make_schedule_with_shift(db_session, "AdminGet", [foreign.id])

    fetched = schedule_service.get_schedule_for_user(db_session, schedule.id, user)
    assert fetched.id == schedule.id


def test_get_schedule_for_user_not_found(db_session):
    from app.core.exceptions import NotFoundException

    user, _ = _employee_with_user_team(db_session, role="admin")
    try:
        schedule_service.get_schedule_for_user(db_session, 99999, user)
        raise AssertionError("expected NotFoundException")
    except NotFoundException:
        pass