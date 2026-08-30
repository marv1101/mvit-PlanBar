from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.schedule import Shiftplan
from app.db.models.user import User
from app.services.sync_actions.base import RoleRequired
from app.services.sync_actions.serializers import serialize_shift as _serialize_shift


class UpdateShift(RoleRequired):
    resource = "shifts"
    action = "update"
    role = RoleRequired()
    _EDITABLE_FIELDS = (
        "employee_id",
        "date",
        "shift_id",
        "start_time",
        "end_time",
        "week",
        "break_start",
        "break_end",
        "label",
        "notes",
    )

    @staticmethod
    def execute(db: Session, data: dict[str, Any], _user: User) -> dict[str, Any]:
        from datetime import date as _date
        from datetime import time as _time

        shift_id = data.get("id")
        shift = db.query(Shiftplan).filter(Shiftplan.id == shift_id).first()
        if not shift:
            raise HTTPException(status_code=404, detail="Shift not found")
        for field in UpdateShift._EDITABLE_FIELDS:
            if field in data:
                value = data[field]
                # Coerce ISO date strings to date objects (SQLite Date column)
                if field == "date" and isinstance(value, str):
                    value = _date.fromisoformat(value)
                # Coerce HH:MM time strings to time objects (SQLite Time columns)
                if field in ("start_time", "end_time") and isinstance(value, str):
                    hh, mm = value.split(":", 1)
                    value = _time(int(hh), int(mm))
                setattr(shift, field, value)
        db.commit()
        db.refresh(shift)
        return _serialize_shift(shift)
