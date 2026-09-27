from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User
from app.services.schedule_service import wish_week_for_date
from app.services.sync_actions.base import RoleRequired
from app.services.sync_actions.serializers import serialize_wish as _serialize_wish


class EmployeeRoleCheck(RoleRequired):
    def check(self, user: User) -> None:
        if not hasattr(user, "employee_id") or user.employee_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User must be an employee")


class CreateShiftWish(RoleRequired):
    resource = "requests"
    action = "create"
    role = EmployeeRoleCheck()

    @staticmethod
    def execute(db: Session, data: dict[str, Any], user: User) -> dict[str, Any]:
        from datetime import date as _date

        date_value = data["date"]
        if isinstance(date_value, str):
            date_value = _date.fromisoformat(date_value)
        employee_id = data.get("employee_id") or user.employee_id
        if employee_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="employee_id is required")
        wish = ShiftWish(
            employee_id=employee_id,
            date=date_value,
            week=wish_week_for_date(date_value),
            type=data.get("type", "preferred"),
            note=data.get("note"),
            status="pending",
        )
        db.add(wish)
        db.commit()
        db.refresh(wish)
        return _serialize_wish(wish)
