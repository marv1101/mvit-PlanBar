from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.services import team_service


class RoleRequired:
    """Base class for role/permission checks.

    Subclasses override `check(user, db, data)` to raise `HTTPException(403)`
    when the user is not allowed to run the action. The default implementation
    permits every authenticated user.

    `db` and `data` enable resource-level ownership checks (e.g. a wish may
    only be edited by its owner or a planner of the owning team).
    """

    def check(self, user: User, db: Session, data: dict[str, Any]) -> None:
        return None


def assert_access_to_employee(db: Session, user: User, employee_id: Any) -> None:
    """Raise 403 unless *user* may access *employee_id* (admin / team scope / own).

    Same semantics as ``team_service.user_can_access_employee``, which backs the
    regular REST endpoints. No-op when *employee_id* is None — the action's
    ``execute`` decides how to treat a missing id (usually 400).
    """
    if employee_id is None:
        return
    if not team_service.user_can_access_employee(db, user, employee_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


def assert_roles(user: User, roles: tuple[str, ...], detail: str) -> None:
    """Raise 403 unless ``user.role`` is one of *roles*."""
    if user.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
