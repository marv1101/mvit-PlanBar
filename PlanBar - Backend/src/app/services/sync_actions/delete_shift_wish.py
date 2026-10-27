from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User
from app.services.sync_actions.base import RoleRequired, assert_access_to_employee


class WishDeleteRoleCheck(RoleRequired):
    """Mirror of DELETE /requests/{id}: the user may access the wish's
    employee (own / planer team scope / admin).
    """

    def check(self, user: User, db: Session, data: dict[str, Any]) -> None:
        wish = db.query(ShiftWish).filter(ShiftWish.id == data.get("id")).first()
        if not wish:
            return  # execute raises the canonical 404
        assert_access_to_employee(db, user, wish.employee_id)


class DeleteShiftWish(RoleRequired):
    resource = "requests"
    action = "delete"
    role = WishDeleteRoleCheck()

    @staticmethod
    def execute(db: Session, data: dict[str, Any], user: User) -> dict[str, Any]:
        wish_id = data.get("id")
        wish = db.query(ShiftWish).filter(ShiftWish.id == wish_id).first()
        if not wish:
            raise HTTPException(status_code=404, detail="Shift wish not found")
        db.delete(wish)
        db.commit()
        return {"id": wish_id, "deleted": True}
