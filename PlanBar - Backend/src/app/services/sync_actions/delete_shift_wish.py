from typing import Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User
from app.services.sync_actions.base import RoleRequired


class DeleteShiftWish(RoleRequired):
    resource = "requests"
    action = "delete"
    role = RoleRequired()

    @staticmethod
    def execute(db: Session, data: dict[str, Any], user: User) -> dict[str, Any]:
        wish_id = data.get("id")
        wish = db.query(ShiftWish).filter(ShiftWish.id == wish_id).first()
        if not wish:
            raise HTTPException(status_code=404, detail="Shift wish not found")
        if user.employee_id != wish.employee_id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")
        db.delete(wish)
        db.commit()
        return {"id": wish_id, "deleted": True}
