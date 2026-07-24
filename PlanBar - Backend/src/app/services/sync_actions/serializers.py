"""Serializers for sync actions, extracted to break circular import."""

from typing import Any
from app.db.models.employee import Employee
from app.db.models.role import Role
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.shift_wish import ShiftWish


def serialize_employee(emp: Employee) -> dict[str, Any]:
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


def serialize_role(role: Role) -> dict[str, Any]:
    return {"id": role.id, "name": role.name, "color": role.color or "#3b82f6"}


def serialize_schedule(sch: Schedule) -> dict[str, Any]:
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


def serialize_shift(sp: Shiftplan) -> dict[str, Any]:
    def _t(v):
        # Time columns come back as datetime.time objects after refresh —
        # the sync client expects "HH:MM" strings.
        if v is None:
            return None
        if hasattr(v, "strftime"):
            return v.strftime("%H:%M")
        return v

    return {
        "id": sp.id,
        "schedule_id": sp.schedule_id,
        "employee_id": sp.employee_id,
        "date": str(sp.date) if sp.date else "",
        "shift_id": sp.shift_id,
        "start_time": _t(sp.start_time),
        "end_time": _t(sp.end_time),
        "week": sp.week,
        "break_start": sp.break_start,
        "break_end": sp.break_end,
        "label": sp.label,
        "notes": sp.notes,
        "created_at": str(sp.created_at) if hasattr(sp, "created_at") and sp.created_at else "",
        "updated_at": str(sp.updated_at) if hasattr(sp, "updated_at") and sp.updated_at else "",
    }


def serialize_wish(wish: ShiftWish) -> dict[str, Any]:
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
