"""Role-based data scoping for the sync endpoints.

The sync endpoints must never expose more data than the corresponding
regular REST resources. These helpers mirror the visibility semantics of
``employees.list_employees_endpoint``, ``requests.list_shift_wishes`` and
``schedule_service.list_schedules_for``:

- **admin**: full dataset
- **planer**: team scope (employees/wishes via ``team_service``,
  schedules via ``list_schedules_for``)
- **user**: only their own employee record, their own wishes and the
  schedules/shifts of the teams they belong to

``roles`` is pure reference data (id/name/color, no PII) and is returned
unscoped so every client can render schedule role requirements.
"""

from sqlalchemy.orm import Session

from app.db.models.employee import Employee
from app.db.models.role import Role
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User
from app.services import schedule_service, team_service


def scoped_employees(db: Session, user: User) -> list[Employee]:
    """Employees visible to *user* (admin: all, planer: team scope, user: own record)."""
    if user.role == "admin":
        return db.query(Employee).all()
    if user.role == "planer":
        team_ids = team_service.get_team_ids_for_user(db, user)
        if not team_ids:
            return []
        return team_service.filter_query_by_team_scope(db.query(Employee), Employee, team_ids).distinct().all()
    return db.query(Employee).filter(Employee.id == user.employee_id).all()


def scoped_roles(db: Session, user: User) -> list[Role]:
    """Role reference data — identical for every role (no PII). *user* is unused by design."""
    return db.query(Role).all()


def scoped_schedules(db: Session, user: User) -> list[Schedule]:
    """Schedules visible to *user* (same semantics as GET /schedules)."""
    return schedule_service.list_schedules_for(db, user)


def scoped_shifts(db: Session, user: User) -> list[Shiftplan]:
    """Shiftplans of the schedules visible to *user* (plan-view parity)."""
    schedule_ids = [schedule.id for schedule in scoped_schedules(db, user)]
    if not schedule_ids:
        return []
    return db.query(Shiftplan).filter(Shiftplan.schedule_id.in_(schedule_ids)).all()


def scoped_wishes(db: Session, user: User) -> list[ShiftWish]:
    """Shift wishes visible to *user* (same semantics as GET /requests)."""
    query = db.query(ShiftWish)
    if user.role == "planer":
        team_ids = team_service.get_team_ids_for_user(db, user)
        if team_ids:
            query = team_service.filter_query_by_team_scope(query, ShiftWish, team_ids)
        else:
            query = query.filter(ShiftWish.employee_id == -1)
    elif user.role != "admin":
        query = query.filter(ShiftWish.employee_id == user.employee_id)
    return query.all()
