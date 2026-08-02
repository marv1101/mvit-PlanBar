"""Tests for Team model and team_service.

Test-driven development: these tests define the desired behaviour for the
new Team entity, the employee_teams M2M relationship and the team_service
CRUD operations.
"""

import uuid

from app.core.enums import UserRole
from app.db.models.employee import Employee
from app.db.models.team import Team
from app.db.models.user import User
from app.schemas.team import TeamCreate, TeamUpdate
from app.services import team_service


def _unique_name(prefix: str = "UnitTeam") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def test_user_role_enum_includes_planer():
    assert UserRole("planer") is UserRole.PLANNER
    values = {role.value for role in UserRole}
    assert {"user", "admin", "planer"}.issubset(values)


def test_team_model_defaults(db_session):
    team = Team(name=_unique_name("Apotheke Nord"), color="#123456")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    assert team.id is not None
    assert team.name.startswith("Apotheke Nord")
    assert team.color == "#123456"
    assert team.created_at is not None
    assert team.updated_at is not None


def test_employee_team_many_to_many(db_session):
    team = Team(name=_unique_name("T1"))
    emp = Employee(first_name="Anna", last_name="Müller")
    db_session.add_all([team, emp])
    db_session.commit()

    emp.teams.append(team)
    db_session.commit()
    db_session.refresh(emp)
    db_session.refresh(team)

    assert [t.id for t in emp.teams] == [team.id]
    assert [e.id for e in team.employees] == [emp.id]


def test_team_service_create(db_session):
    team = team_service.create_team(
        db_session,
        TeamCreate(name=_unique_name("Apotheke Süd"), color="#abcdef", description="Team Süd"),
        actor_id=None,
    )
    assert team.id is not None
    assert team.name.startswith("Apotheke Süd")
    assert team.color == "#abcdef"
    assert team.description == "Team Süd"


def test_team_service_list(db_session):
    name_a = _unique_name("List A")
    name_b = _unique_name("List B")
    team_service.create_team(db_session, TeamCreate(name=name_a))
    team_service.create_team(db_session, TeamCreate(name=name_b))

    teams = team_service.list_teams(db_session)
    names = [t.name for t in teams]
    assert name_a in names
    assert name_b in names


def test_team_service_update(db_session):
    team = team_service.create_team(db_session, TeamCreate(name=_unique_name("Original")))
    updated = team_service.update_team(
        db_session,
        team.id,
        TeamUpdate(name=_unique_name("Renamed"), color="#000000", description="updated"),
    )
    assert updated.name.startswith("Renamed")
    assert updated.color == "#000000"
    assert updated.description == "updated"


def test_team_service_delete(db_session):
    team = team_service.create_team(db_session, TeamCreate(name=_unique_name("ToDelete")))
    team_service.delete_team(db_session, team.id)

    from app.core.exceptions import NotFoundException

    try:
        team_service.get_team(db_session, team.id)
        raise AssertionError("expected NotFoundException")
    except NotFoundException:
        pass


def test_team_service_assign_employees(db_session):
    team = team_service.create_team(db_session, TeamCreate(name=_unique_name("AssignTeam")))
    emp1 = Employee(first_name="A", last_name="B")
    emp2 = Employee(first_name="C", last_name="D")
    db_session.add_all([emp1, emp2])
    db_session.commit()

    team_service.assign_employees(db_session, team.id, [emp1.id, emp2.id])

    db_session.refresh(team)
    ids = sorted(e.id for e in team.employees)
    assert ids == sorted([emp1.id, emp2.id])


def test_team_service_get_teams_for_user_admin(db_session):
    """Admins have no team restriction — returns empty list (no filter)."""
    user = User(
        username=_unique_name("unit_admin_user"),
        email=f"{_unique_name('admin').lower()}@example.com",
        password_hash="x",
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    teams = team_service.get_teams_for_user(db_session, user)
    assert teams == []


def test_team_service_get_teams_for_user_planer(db_session):
    team = team_service.create_team(db_session, TeamCreate(name=_unique_name("PlanerTeam")))
    emp = Employee(first_name="Plan", last_name="Er", user_id=None)
    db_session.add(emp)
    db_session.commit()
    emp.teams.append(team)
    db_session.commit()

    user = User(
        username=_unique_name("unit_planer_user"),
        email=f"{_unique_name('planer').lower()}@example.com",
        password_hash="x",
        role="planer",
        employee_id=emp.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    teams = team_service.get_teams_for_user(db_session, user)
    assert [t.id for t in teams] == [team.id]


def test_team_service_employee_team_ids(db_session):
    team = team_service.create_team(db_session, TeamCreate(name=_unique_name("X")))
    emp = Employee(first_name="x", last_name="y")
    db_session.add(emp)
    db_session.commit()
    emp.teams.append(team)
    db_session.commit()
    db_session.refresh(emp)

    ids = team_service.get_team_ids_for_employee(db_session, emp.id)
    assert ids == [team.id]


def test_get_teams_for_user_falls_back_to_employee_user_id(db_session):
    """Legacy/one-sided links (only employee.user_id set) must resolve the teams.

    Regression: planners whose user.employee_id is NULL but whose Employee
    row has user_id set were treated as having no teams, breaking planning.
    """
    team = team_service.create_team(db_session, TeamCreate(name=_unique_name("LegacyTeam")))
    user = User(
        username=_unique_name("legacy_planer"),
        email=f"{_unique_name('legacy').lower()}@example.com",
        password_hash="x",
        role="planer",
        employee_id=None,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    emp = Employee(first_name="Legacy", last_name="Planer", user_id=user.id)
    db_session.add(emp)
    db_session.commit()
    emp.teams.append(team)
    db_session.commit()

    assert user.employee_id is None
    assert [t.id for t in team_service.get_teams_for_user(db_session, user)] == [team.id]
    assert team_service.get_team_ids_for_user(db_session, user) == [team.id]


def test_get_teams_for_user_prefers_canonical_employee_id(db_session):
    """When both FK directions point at different employees, user.employee_id wins."""
    canonical = team_service.create_team(db_session, TeamCreate(name=_unique_name("Canonical")))
    other = team_service.create_team(db_session, TeamCreate(name=_unique_name("ReverseOnly")))
    canonical_emp = Employee(first_name="Canonical", last_name="Emp")
    reverse_emp = Employee(first_name="Reverse", last_name="Emp")
    db_session.add_all([canonical_emp, reverse_emp])
    db_session.commit()
    canonical_emp.teams.append(canonical)
    reverse_emp.teams.append(other)
    db_session.commit()

    user = User(
        username=_unique_name("dual_link_user"),
        email=f"{_unique_name('dual').lower()}@example.com",
        password_hash="x",
        role="planer",
        employee_id=canonical_emp.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    reverse_emp.user_id = user.id
    db_session.commit()

    assert [t.id for t in team_service.get_teams_for_user(db_session, user)] == [canonical.id]
    assert team_service.get_team_ids_for_user(db_session, user) == [canonical.id]


def test_get_teams_for_user_no_employee_returns_empty(db_session):
    """A planer without any link to an employee still gets no teams (no crash)."""
    user = User(
        username=_unique_name("unlinked_planer"),
        email=f"{_unique_name('unlinked').lower()}@example.com",
        password_hash="x",
        role="planer",
        employee_id=None,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert team_service.get_teams_for_user(db_session, user) == []
    assert team_service.get_team_ids_for_user(db_session, user) == []
