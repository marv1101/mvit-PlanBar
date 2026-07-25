from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.db.models.employee import Employee
from app.db.models.team import Team
from app.schemas.team import TeamCreate, TeamUpdate
from app.services import audit_service


def get_team(db: Session, team_id: int) -> Team:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise NotFoundException(detail="Team not found")
    return team


def list_teams(db: Session, offset: int = 0, limit: int | None = None) -> list[Team]:
    query = db.query(Team).order_by(Team.name)
    if limit is not None:
        query = query.offset(offset).limit(limit)
    return query.all()


def create_team(db: Session, data: TeamCreate, actor_id: int | None = None) -> Team:
    team = Team(name=data.name, color=data.color, description=data.description)
    db.add(team)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictException(detail="Team with this name already exists")
    db.refresh(team)
    audit_service.log_create(db, user_id=actor_id, resource_type="team", resource_id=str(team.id))
    return team


def update_team(
    db: Session,
    team_id: int,
    data: TeamUpdate,
    actor_id: int | None = None,
) -> Team:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise NotFoundException(detail="Team not found")
    if data.name is not None:
        team.name = data.name
    if data.color is not None:
        team.color = data.color
    if data.description is not None:
        team.description = data.description
    db.add(team)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictException(detail="Team with this name already exists")
    db.refresh(team)
    audit_service.log_update(db, user_id=actor_id, resource_type="team", resource_id=str(team.id))
    return team


def delete_team(db: Session, team_id: int, actor_id: int | None = None) -> None:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise NotFoundException(detail="Team not found")
    db.delete(team)
    db.commit()
    audit_service.log_delete(db, user_id=actor_id, resource_type="team", resource_id=str(team_id))


def assign_employees(db: Session, team_id: int, employee_ids: list[int], actor_id: int | None = None) -> Team:
    """Add employees to a team (additive; existing members are kept).

    Use ``remove_employees`` to drop members.
    """
    team = get_team(db, team_id)
    existing_ids = {e.id for e in team.employees}
    new_ids = {i for i in employee_ids if i not in existing_ids}
    if new_ids:
        new_emps = db.query(Employee).filter(Employee.id.in_(new_ids)).all()
        team.employees.extend(new_emps)
    db.add(team)
    db.commit()
    db.refresh(team)
    audit_service.log_update(
        db,
        user_id=actor_id,
        resource_type="team",
        resource_id=str(team.id),
        details=f"add_employees ids={sorted(employee_ids)}",
    )
    return team


def remove_employees(db: Session, team_id: int, employee_ids: list[int], actor_id: int | None = None) -> Team:
    team = get_team(db, team_id)
    keep = [e for e in team.employees if e.id not in set(employee_ids)]
    team.employees = keep
    db.add(team)
    db.commit()
    db.refresh(team)
    audit_service.log_update(
        db,
        user_id=actor_id,
        resource_type="team",
        resource_id=str(team.id),
        details=f"remove_employees ids={sorted(employee_ids)}",
    )
    return team


def get_team_ids_for_employee(db: Session, employee_id: int | None) -> list[int]:
    if employee_id is None:
        return []
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        return []
    return [t.id for t in emp.teams]


def get_teams_for_user(db: Session, user) -> list[Team]:
    """Return the teams the given user may operate on.

    Admins get an empty list (no team restriction; can access all teams).
    Planners and regular users get the teams of their linked employee.
    """
    if user.role == "admin":
        return []

    if not user.employee_id:
        return []

    emp = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not emp:
        return []
    return list(emp.teams)


def get_team_ids_for_user(db: Session, user) -> list[int]:
    """Return team ids the user can operate on, or [] meaning 'no restriction' (admin) or 'no teams'."""
    if user.role == "admin":
        return []  # admin filter operates elsewhere
    return get_team_ids_for_employee(db, user.employee_id)


def is_team_restricted(user) -> bool:
    """True when the user is restricted to specific teams (planner/employee). Admins are not."""
    return user.role != "admin"


def employee_in_teams(db: Session, employee_id: int, team_ids: list[int]) -> bool:
    """True if employee is member of any of the given team ids."""
    if not team_ids:
        return False
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        return False
    emp_team_ids = {t.id for t in emp.teams}
    return bool(emp_team_ids.intersection(team_ids))