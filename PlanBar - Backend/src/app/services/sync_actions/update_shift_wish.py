from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User
from app.services.sync_actions.base import RoleRequired
from app.services.sync_actions.serializers import serialize_wish as _serialize_wish


class UpdateShiftWish(RoleRequired):
    resource = "requests"
    action = "update"
    role = RoleRequired()

    @staticmethod
    def execute(db: Session, data: dict[str, Any], user: User) -> dict[str, Any]:
        wish_id = data.get("id")
        wish = db.query(ShiftWish).filter(ShiftWish.id == wish_id).first()
        if not wish:
            raise HTTPException(status_code=404, detail="Shift wish not found")
        if user.employee_id != wish.employee_id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")
        if "employee_id" in data:
            wish.employee_id = data["employee_id"]
        if "date" in data:
            wish.date = data["date"]
        if "type" in data:
            wish.type = data["type"]
        if "note" in data:
            wish.note = data["note"]
        db.commit()
        db.refresh(wish)
        return _serialize_wish(wish)
