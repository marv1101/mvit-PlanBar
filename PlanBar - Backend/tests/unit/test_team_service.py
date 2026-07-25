"""Tests for Team model and team_service.

Test-driven development: these tests define the desired behaviour for the
new Team entity, the employee_teams M2M relationship and the team_service
CRUD operations.
"""

from app.core.enums import UserRole
from app.db.models.employee import Employee
from app.db.models.team import Team
from app.db.models.user import User
from app.schemas.team import TeamCreate, TeamUpdate
from app.services import team_service


def test_user_role_enum_includes_planer():
    assert UserRole("planer") is UserRole.PLANNER
    values = {role.value for role in UserRole}
    assert {"user", "admin", "planer"}.issubset(values)


def test_team_model_defaults(db_session):
    team = Team(name="Apotheke Nord", color="#123456")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    assert team.id is not None
    assert team.name == "Apotheke Nord"
    assert team.color == "#123456"
    assert team.created_at is not None
    assert team.updated_at is not None


def test_employee_team_many_to_many(db_session):
    team = Team(name="T1")
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
        TeamCreate(name="Apotheke Süd", color="#abcdef", description="Team Süd"),
        actor_id=None,
    )
    assert team.id is not None
    assert team.name == "Apotheke Süd"
    assert team.color == "#abcdef"
    assert team.description == "Team Süd"


def test_team_service_list(db_session):
    team_service.create_team(db_session, TeamCreate(name="List A"))
    team_service.create_team(db_session, TeamCreate(name="List B"))

    teams = team_service.list_teams(db_session)
    names = [t.name for t in teams]
    assert "List A" in names
    assert "List B" in names


def test_team_service_update(db_session):
    team = team_service.create_team(db_session, TeamCreate(name="Original"))
    updated = team_service.update_team(
        db_session,
        team.id,
        TeamUpdate(name="Renamed", color="#000000", description="updated"),
    )
    assert updated.name == "Renamed"
    assert updated.color == "#000000"
    assert updated.description == "updated"


def test_team_service_delete(db_session):
    team = team_service.create_team(db_session, TeamCreate(name="ToDelete"))
    team_service.delete_team(db_session, team.id)

    from app.core.exceptions import NotFoundException

    try:
        team_service.get_team(db_session, team.id)
        raise AssertionError("expected NotFoundException")
    except NotFoundException:
        pass


def test_team_service_assign_employees(db_session):
    team = team_service.create_team(db_session, TeamCreate(name="AssignTeam"))
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
        username="unit_admin_user",
        email="unit_admin@example.com",
        password_hash="x",
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    teams = team_service.get_teams_for_user(db_session, user)
    assert teams == []


def test_team_service_get_teams_for_user_planer(db_session):
    team = team_service.create_team(db_session, TeamCreate(name="PlanerTeam"))
    emp = Employee(first_name="Plan", last_name="Er", user_id=None)
    db_session.add(emp)
    db_session.commit()
    emp.teams.append(team)
    db_session.commit()

    user = User(
        username="unit_planer_user",
        email="unit_planer@example.com",
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
    team = team_service.create_team(db_session, TeamCreate(name="X"))
    emp = Employee(first_name="x", last_name="y")
    db_session.add(emp)
    db_session.commit()
    emp.teams.append(team)
    db_session.commit()
    db_session.refresh(emp)

    ids = team_service.get_team_ids_for_employee(db_session, emp.id)
    assert ids == [team.id]