from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.user import User
from app.services.schedule_service import (
    _assert_date_in_scope,
    _assert_team_restriction_for_employee_ids,
    _get_week_type,
    assert_team_read_access,
)
from app.services.sync_actions.base import RoleRequired, assert_roles
from app.services.sync_actions.serializers import serialize_shift as _serialize_shift


class ShiftUpdateRoleCheck(RoleRequired):
    """Mirror of PUT /schedules/{id}/shifts/{shiftplan_id}: admin/planer only,
    the shift's schedule must be within the user's read scope and an employee
    reassignment must stay within the planer's team scope.
    """

    def check(self, user: User, db: Session, data: dict[str, Any]) -> None:
        assert_roles(user, ("admin", "planer"), "Admin or planer access required")
        shift = db.query(Shiftplan).filter(Shiftplan.id == data.get("id")).first()
        if not shift:
            return  # execute raises the canonical 404
        schedule = db.query(Schedule).filter(Schedule.id == shift.schedule_id).first()
        if schedule:
            try:
                assert_team_read_access(db, schedule, user)
            except PermissionError:
                raise HTTPException(status_code=403, detail="Schedule is not in your team scope")
        new_employee_id = data.get("employee_id") or shift.employee_id
        try:
            _assert_team_restriction_for_employee_ids(db, {new_employee_id}, user)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Planer may only assign employees from their own teams")


class UpdateShift(RoleRequired):
    resource = "shifts"
    action = "update"
    role = ShiftUpdateRoleCheck()
    _EDITABLE_FIELDS = (
        "employee_id",
        "date",
        "shift_id",
        "start_time",
        "end_time",
        "break_start",
        "break_end",
        "label",
        "notes",
    )

    @staticmethod
    def execute(db: Session, data: dict[str, Any], user: User) -> dict[str, Any]:
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
                # Coerce HH:MM time strings to time objects (SQLite Time column)
                if field in ("start_time", "end_time") and isinstance(value, str):
                    hh, mm = value.split(":", 1)
                    value = _time(int(hh), int(mm))
                setattr(shift, field, value)
        if "date" in data:
            schedule = db.query(Schedule).filter(Schedule.id == shift.schedule_id).first()
            if schedule:
                try:
                    _assert_date_in_scope(schedule, shift.date)
                except ValueError as e:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
            shift.week = _get_week_type(shift.date)
        db.commit()
        db.refresh(shift)
        return _serialize_shift(shift)
