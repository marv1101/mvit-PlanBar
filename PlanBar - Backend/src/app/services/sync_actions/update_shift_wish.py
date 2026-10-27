from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User
from app.services.schedule_service import wish_week_for_date
from app.services.sync_actions.base import RoleRequired, assert_access_to_employee
from app.services.sync_actions.serializers import serialize_wish as _serialize_wish


class WishUpdateRoleCheck(RoleRequired):
    """Mirror of PUT /requests/{id}: the user may access the wish's employee
    (own / planer team scope / admin) and any employee the wish is moved to.
    Only admins and planners may change the wish status.
    """

    def check(self, user: User, db: Session, data: dict[str, Any]) -> None:
        wish = db.query(ShiftWish).filter(ShiftWish.id == data.get("id")).first()
        if not wish:
            return  # execute raises the canonical 404
        assert_access_to_employee(db, user, wish.employee_id)
        if data.get("employee_id") is not None:
            assert_access_to_employee(db, user, data["employee_id"])
        if data.get("status") is not None and user.role == "user":
            raise HTTPException(status_code=403, detail="Only admins or planners can update wish status")


class UpdateShiftWish(RoleRequired):
    resource = "requests"
    action = "update"
    role = WishUpdateRoleCheck()

    @staticmethod
    def execute(db: Session, data: dict[str, Any], user: User) -> dict[str, Any]:
        from datetime import date as _date

        wish_id = data.get("id")
        wish = db.query(ShiftWish).filter(ShiftWish.id == wish_id).first()
        if not wish:
            raise HTTPException(status_code=404, detail="Shift wish not found")
        if "employee_id" in data:
            wish.employee_id = data["employee_id"]
        if "date" in data:
            date_value = data["date"]
            if isinstance(date_value, str):
                date_value = _date.fromisoformat(date_value)
            wish.date = date_value
            wish.week = wish_week_for_date(date_value)
        if "type" in data:
            wish.type = data["type"]
        if "note" in data:
            wish.note = data["note"]
        if "status" in data and data["status"] is not None:
            wish.status = data["status"]
        db.commit()
        db.refresh(wish)
        return _serialize_wish(wish)
