from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.versioning import ConflictError, compute_etag, detect_conflict
from app.db.models.schedule import Schedule
from app.db.models.user import User
from app.services.sync_actions.base import RoleRequired
from app.services.sync_actions.serializers import serialize_schedule as _serialize_schedule


class AdminRoleCheck(RoleRequired):
    def check(self, user: User) -> None:
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")


class UpdateSchedule(RoleRequired):
    resource = "schedules"
    action = "update"
    role = AdminRoleCheck()

    @staticmethod
    def execute(db: Session, data: dict[str, Any], user: User) -> dict[str, Any]:
        schedule_id = data.get("id")
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        schedule_etag = data.get("_etag")
        stored_etag = compute_etag(_serialize_schedule(schedule))
        try:
            detect_conflict(
                schedule.updated_at if hasattr(schedule, "updated_at") else None, schedule_etag, stored_etag
            )
        except ConflictError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        if "name" in data:
            schedule.name = data["name"]
        if "status" in data:
            schedule.status = data["status"]
        if "week_type" in data:
            schedule.week_type = data["week_type"]
        db.commit()
        db.refresh(schedule)
        return _serialize_schedule(schedule)
