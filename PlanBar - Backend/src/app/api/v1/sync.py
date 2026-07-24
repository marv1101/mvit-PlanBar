import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.versioning import (
    ConflictError,
    add_cache_headers,
    check_if_modified_since,
    check_if_none_match,
    compute_etag,
)
from app.db.models.employee import Employee
from app.db.models.role import Role
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User
from app.dependencies import get_current_user, get_db

router = APIRouter()


class ActionPayload(BaseModel):
    resource: str
    action: str  # create | update | delete
    data: dict[str, Any]
    client_timestamp: str


class ActionBatch(BaseModel):
    actions: list[ActionPayload]


class SyncResponse(BaseModel):
    employees: list[dict[str, Any]] = []
    roles: list[dict[str, Any]] = []
    schedules: list[dict[str, Any]] = []
    shifts: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    synced_at: str


def _serialize_employee(emp: Employee) -> dict[str, Any]:
    return {
        "id": emp.id,
        "first_name": emp.first_name,
        "last_name": emp.last_name,
        "email": emp.email or "",
        "color": emp.color or "#3b82f6",
        "working_hours_json": emp.working_hours_json,
        "break_start": emp.break_start,
        "break_end": emp.break_end,
        "max_work_hours": emp.max_work_hours,
        "role_ids": [r.id for r in (emp.roles or [])],
        "created_at": str(emp.created_at) if hasattr(emp, "created_at") and emp.created_at else "",
        "updated_at": str(emp.updated_at) if hasattr(emp, "updated_at") and emp.updated_at else "",
    }


def _serialize_role(role: Role) -> dict[str, Any]:
    return {
        "id": role.id,
        "name": role.name,
        "color": role.color or "#3b82f6",
    }


def _serialize_schedule(sch: Schedule) -> dict[str, Any]:
    return {
        "id": sch.id,
        "name": sch.name,
        "status": sch.status,
        "week_type": sch.week_type,
        "start_date": str(sch.start_date) if sch.start_date else None,
        "end_date": str(sch.end_date) if sch.end_date else None,
        "role_requirements": sch.role_requirements,
        "shift_templates": sch.shift_templates,
        "tito_job_id": sch.tito_job_id,
        "metadata_json": sch.metadata_json,
        "metrics_json": sch.metrics_json,
        "diagnostics_json": sch.diagnostics_json,
        "created_at": str(sch.created_at) if hasattr(sch, "created_at") and sch.created_at else "",
        "updated_at": str(sch.updated_at) if hasattr(sch, "updated_at") and sch.updated_at else "",
    }


def _serialize_shift(sp: Shiftplan) -> dict[str, Any]:
    return {
        "id": sp.id,
        "schedule_id": sp.schedule_id,
        "employee_id": sp.employee_id,
        "date": str(sp.date) if sp.date else "",
        "shift_id": sp.shift_id,
        "start_time": sp.start_time,
        "end_time": sp.end_time,
        "week": sp.week,
        "break_start": sp.break_start,
        "break_end": sp.break_end,
        "label": sp.label,
        "notes": sp.notes,
        "created_at": str(sp.created_at) if hasattr(sp, "created_at") and sp.created_at else "",
        "updated_at": str(sp.updated_at) if hasattr(sp, "updated_at") and sp.updated_at else "",
    }


def _serialize_wish(wish: ShiftWish) -> dict[str, Any]:
    return {
        "id": wish.id,
        "employee_id": wish.employee_id,
        "date": str(wish.date) if wish.date else "",
        "week": wish.week,
        "type": wish.type,
        "note": wish.note,
        "status": wish.status,
        "reviewed_by": wish.reviewed_by,
        "reviewed_at": str(wish.reviewed_at) if wish.reviewed_at else None,
        "rejection_reason": wish.rejection_reason,
    }


def _get_last_updated(items: list[Any]) -> datetime | None:
    """Get the latest updated_at from a list of items."""
    candidates = []
    for item in items:
        if hasattr(item, "updated_at") and item.updated_at:
            candidates.append(item.updated_at)
        elif hasattr(item, "created_at") and item.created_at:
            candidates.append(item.created_at)
    return max(candidates) if candidates else None


@router.get("/sync/initial", response_model=SyncResponse)
def initial_sync(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Bulk endpoint returning all reference data for initial client sync."""
    employees = db.query(Employee).all()
    roles = db.query(Role).all()
    schedules = db.query(Schedule).all()
    shifts = db.query(Shiftplan).all()
    wishes = db.query(ShiftWish).all()

    response_data = SyncResponse(
        employees=[_serialize_employee(e) for e in employees],
        roles=[_serialize_role(r) for r in roles],
        schedules=[_serialize_schedule(s) for s in schedules],
        shifts=[_serialize_shift(s) for s in shifts],
        requests=[_serialize_wish(w) for w in wishes],
        synced_at=datetime.now(timezone.utc).isoformat(),
    )

    all_items = employees + roles + schedules + shifts + wishes
    last_modified = _get_last_updated(all_items)
    etag = compute_etag(response_data.model_dump())

    if request:
        if_none_match = request.headers.get("if-none-match")
        if check_if_none_match(if_none_match, etag):
            raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED)

        if last_modified:
            if_modified_since = request.headers.get("if-modified-since")
            if check_if_modified_since(if_modified_since, last_modified):
                raise HTTPException(status_code=304)

    response = Response(
        content=response_data.model_dump_json(),
        media_type="application/json",
    )
    add_cache_headers(response, etag=etag, last_modified=last_modified)
    return response


@router.get("/sync/{resource_type}")
def delta_sync(
    resource_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    if_none_match: str | None = Header(None),
    if_modified_since: str | None = Header(None),
):
    """Delta sync for individual resource types."""
    resource_type = resource_type.lower()

    serializers = {
        "employees": (Employee, _serialize_employee),
        "roles": (Role, _serialize_role),
        "schedules": (Schedule, _serialize_schedule),
        "shifts": (Shiftplan, _serialize_shift),
        "requests": (ShiftWish, _serialize_wish),
    }

    if resource_type not in serializers:
        raise HTTPException(status_code=404, detail=f"Unknown resource type: {resource_type}")

    model_class, serializer = serializers[resource_type]
    items = db.query(model_class).all()

    last_modified = _get_last_updated(items)
    serialized = [serializer(item) for item in items]
    etag = compute_etag(serialized)

    if check_if_none_match(if_none_match, etag):
        raise HTTPException(status_code=304)

    if last_modified and check_if_modified_since(if_modified_since, last_modified):
        raise HTTPException(status_code=304)

    result = {
        "data": serialized,
        "etag": etag,
        "last_modified": last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT") if last_modified else None,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }

    response = Response(content=json.dumps(result), media_type="application/json")
    add_cache_headers(response, etag=etag, last_modified=last_modified)
    return response


@router.post("/sync/actions", status_code=200)
def sync_actions(
    batch: ActionBatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply a batch of offline actions with conflict detection.

    Each action is dispatched to a `SyncAction` handler via
    `SyncActionRegistry.dispatch()`. Auth checks are owned by the handler's
    `role` attribute — there is exactly one auth choke-point per dispatch.
    """
    from app.services.sync_actions import SyncActionRegistry  # noqa: PLC0415

    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for action in batch.actions:
        try:
            result = SyncActionRegistry.dispatch(action, db, current_user)
            results.append({"resource": action.resource, "action": action.action, "success": True, "data": result})
        except ConflictError as e:
            errors.append(
                {
                    "resource": action.resource,
                    "action": action.action,
                    "success": False,
                    "error": str(e),
                    "conflict": True,
                }
            )
        except HTTPException:
            raise
        except (ValueError, OSError) as e:
            errors.append(
                {
                    "resource": action.resource,
                    "action": action.action,
                    "success": False,
                    "error": str(e),
                }
            )

    return {
        "results": results,
        "errors": errors,
        "total": len(batch.actions),
        "synced": len(results),
        "failed": len(errors),
    }
