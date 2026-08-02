from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query, Session

from app.core.exceptions import ConflictException, NotFoundException
from app.db.models.employee import Employee
from app.db.models.team import Team, employee_teams
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
    """Replace the employees on a team with the given set of employee ids."""
    team = get_team(db, team_id)
    current_ids = {e.id for e in team.employees}
    target_ids = set(employee_ids)

    to_add = target_ids - current_ids
    to_remove = current_ids - target_ids

    if to_add:
        new_emps = db.query(Employee).filter(Employee.id.in_(to_add)).all()
        team.employees.extend(new_emps)
    if to_remove:
        team.employees = [e for e in team.employees if e.id not in to_remove]

    db.add(team)
    db.commit()
    db.refresh(team)
    audit_service.log_update(
        db,
        user_id=actor_id,
        resource_type="team",
        resource_id=str(team.id),
        details=f"set_employees ids={sorted(employee_ids)}",
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


def get_employee_for_user(db: Session, user) -> Employee | None:
    """Resolve the employee linked to a user.

    Prefers the canonical ``user.employee_id`` but falls back to the
    employee whose ``user_id`` references the user, so one-sided/legacy
    links (e.g. only ``employee.user_id`` set) still resolve correctly.
    """
    if user.employee_id:
        emp = db.query(Employee).filter(Employee.id == user.employee_id).first()
        if emp:
            return emp
    return db.query(Employee).filter(Employee.user_id == user.id).first()


def get_teams_for_user(db: Session, user) -> list[Team]:
    """Return the teams the given user may operate on.

    Admins get an empty list (no team restriction; can access all teams).
    Planners and regular users get the teams of their linked employee.
    """
    if user.role == "admin":
        return []

    emp = get_employee_for_user(db, user)
    if not emp:
        return []
    return list(emp.teams)


def get_team_ids_for_user(db: Session, user) -> list[int]:
    """Return team ids the user can operate on, or [] meaning 'no restriction' (admin) or 'no teams'."""
    if user.role == "admin":
        return []  # admin filter operates elsewhere
    emp = get_employee_for_user(db, user)
    if not emp:
        return []
    return [t.id for t in emp.teams]


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


def user_can_access_employee(db: Session, user, employee_id: int) -> bool:
    """Check whether *user* may access the given employee.

    - Admins always have access.
    - Planners have access if the employee belongs to one of their teams.
    - Regular users can only access their own employee record.
    """
    if user.role == "admin":
        return True
    if user.role == "planer":
        return employee_in_teams(db, employee_id, get_team_ids_for_user(db, user))
    return user.employee_id == employee_id


def assert_user_can_access_employee(
    db: Session,
    user,
    employee_id: int,
    *,
    allow_planer: bool = True,
) -> None:
    """Raise if *user* may not access the given employee.

    Same logic as :func:`user_can_access_employee` but raises
    ``PermissionError`` on denial instead of returning ``False``.

    Parameters
    ----------
    allow_planer:
        When ``False``, planners are denied even if the employee is in
        their team scope (used for contract/timecard sub-resources).
    """
    if user.role == "admin":
        return
    if user.role == "planer":
        if not allow_planer:
            raise PermissionError("Planer access not allowed for this resource")
        if not employee_in_teams(db, employee_id, get_team_ids_for_user(db, user)):
            raise PermissionError("Employee is not in your team scope")
        return
    if user.employee_id != employee_id:
        raise PermissionError("Not authorized")


def filter_query_by_team_scope(
    query: Query,
    entity,
    team_ids: list[int],
) -> Query:
    """Filter *query* so only rows whose employee belongs to one of *team_ids* remain.

    Works for any SQLAlchemy entity that has an ``employee_id`` column
    (e.g. ``Shiftplan``, ``ShiftWish``) or an ``id`` column that *is* the
    employee id (``Employee`` itself).

    Returns an unmodified query when *team_ids* is empty (no restriction).
    """
    if not team_ids:
        return query.filter(False)
    emp_col = getattr(entity, "employee_id", None) or entity.id
    return (
        query
        .join(employee_teams, employee_teams.c.employee_id == emp_col)
        .filter(employee_teams.c.team_id.in_(team_ids))
    )
