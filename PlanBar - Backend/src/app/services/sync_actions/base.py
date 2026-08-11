from typing import Any

from sqlalchemy.orm import Session

from app.db.models.user import User


class RoleRequired:
    """Base class for role/permission checks.

    Subclasses override `check(user)` to raise `HTTPException(403)` when
    the user is not allowed to run the action. The default implementation
    permits every authenticated user.
    """

    def check(self, user: User) -> None:
        return None


class SyncAction:
    """Base class for sync actions (strategy pattern).

    Subclasses MUST set `resource: str`, `action: str`, and `role: RoleRequired`.
    Subclasses MUST implement `execute(db, data, user)`.
    """

    resource: str = ""
    action: str = ""
    role: RoleRequired = RoleRequired()

    def execute(self, db: Session, data: dict[str, Any], user: User) -> dict[str, Any]:
        raise NotImplementedError
