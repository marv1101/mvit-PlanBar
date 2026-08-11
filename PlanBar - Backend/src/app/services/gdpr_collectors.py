"""DSGVO Art. 20 data collectors — split from gdpr_service.py for SRP.

Each collector is responsible for gathering and serializing one data category
associated with a user. The orchestrator (``export_user_data``) calls them in
sequence and assembles the final export payload. The contract of every
collector is:

* Input: a ``sqlalchemy.orm.Session`` and ``user_id: int``
* Output: a JSON-serializable ``dict`` (or ``list`` of dicts) that can be
  safely passed to ``json.dumps``.

The collectors are pure read-only side effects — they never mutate state.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog
from app.db.models.employee import Employee
from app.db.models.pinboard import PinboardMessage, PinboardThread
from app.db.models.user import User

# ---------------------------------------------------------------------------
# Serialization helpers (shared by all collectors)
# ---------------------------------------------------------------------------


def serialize_datetime(dt) -> str | None:
    """ISO-8601 string for a ``datetime`` (or ``None``)."""
    if dt is None:
        return None
    return dt.isoformat()


def serialize_date(d) -> str | None:
    """ISO-8601 string for a ``date`` (or ``None``)."""
    if d is None:
        return None
    return d.isoformat()


# ---------------------------------------------------------------------------
# Per-category collectors
# ---------------------------------------------------------------------------


def collect_user(db: Session, user_id: int) -> dict[str, Any] | None:
    """Return the user profile block, or ``None`` if the user does not exist."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "must_change_password": user.must_change_password,
        "created_at": serialize_datetime(user.created_at),
        "updated_at": serialize_datetime(user.updated_at),
        "last_login": serialize_datetime(user.last_login),
    }


def _linked_employees(db: Session, user: User) -> list[Employee]:
    """Return the de-duplicated list of employees linked to ``user``."""
    employees_list = db.query(Employee).filter(Employee.user_id == user.id).all()
    if user.employee_id is not None:
        extra = db.query(Employee).filter(Employee.id == user.employee_id).first()
        if extra is not None and extra not in employees_list:
            employees_list.append(extra)
    return employees_list


def collect_employee_contracts(employee: Employee) -> list[dict[str, Any]]:
    """Return the contract rows for an employee."""
    return [
        {
            "id": c.id,
            "weekly_working_hours": c.weekly_working_hours,
            "break_time": c.break_time,
            "hired_role": c.hired_role,
            "created_at": serialize_datetime(c.created_at),
            "updated_at": serialize_datetime(c.updated_at),
        }
        for c in employee.contracts
    ]


def collect_employee_timecards(employee: Employee) -> list[dict[str, Any]]:
    """Return the timecard rows for an employee."""
    return [
        {
            "id": t.id,
            "week": t.week,
            "year": t.year,
            "balance": t.balance,
            "scheduled_hours": t.scheduled_hours,
            "actual_hours": t.actual_hours,
            "contract_hours": t.contract_hours,
            "manual_adjustment_hours": t.manual_adjustment_hours,
            "adjustment_reason": t.adjustment_reason,
            "created_at": serialize_datetime(t.created_at),
            "updated_at": serialize_datetime(t.updated_at),
        }
        for t in employee.timecards
    ]


def collect_employee_shift_wishes(employee: Employee) -> list[dict[str, Any]]:
    """Return the shift-wish rows for an employee."""
    return [
        {
            "id": sw.id,
            "date": serialize_date(sw.date),
            "week": sw.week,
            "type": sw.type,
            "note": sw.note,
            "status": sw.status,
            "reviewed_by": sw.reviewed_by,
            "reviewed_at": serialize_datetime(sw.reviewed_at),
            "rejection_reason": sw.rejection_reason,
            "created_at": serialize_datetime(sw.created_at),
            "updated_at": serialize_datetime(sw.updated_at),
        }
        for sw in employee.shift_wishes
    ]


def collect_employee_shiftplans(db: Session, employee: Employee) -> list[dict[str, Any]]:
    """Return the shiftplan rows referencing an employee."""
    # Imported lazily here (same as the pre-refactor implementation) to avoid
    # circular imports at module load time.
    from app.db.models.schedule import Shiftplan as ShiftplanModel

    rows = db.query(ShiftplanModel).filter(ShiftplanModel.employee_id == employee.id).all()
    return [
        {
            "id": sp.id,
            "schedule_id": sp.schedule_id,
            "date": serialize_date(sp.date),
            "shift_id": sp.shift_id,
            "start_time": sp.start_time.isoformat() if sp.start_time else None,
            "end_time": sp.end_time.isoformat() if sp.end_time else None,
            "label": sp.label,
            "notes": sp.notes,
            "created_at": serialize_datetime(sp.created_at),
        }
        for sp in rows
    ]


def collect_employees(db: Session, user: User) -> list[dict[str, Any]]:
    """Return one block per linked employee, including nested sub-collections."""
    return [
        {
            "id": employee.id,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "email": employee.email,
            "color": employee.color,
            "working_hours_json": employee.working_hours_json,
            "break_start": employee.break_start,
            "break_end": employee.break_end,
            "max_work_hours": employee.max_work_hours,
            "created_at": serialize_datetime(employee.created_at),
            "updated_at": serialize_datetime(employee.updated_at),
            "contracts": collect_employee_contracts(employee),
            "timecards": collect_employee_timecards(employee),
            "shift_wishes": collect_employee_shift_wishes(employee),
            "shiftplans": collect_employee_shiftplans(db, employee),
        }
        for employee in _linked_employees(db, user)
    ]


def collect_pinboard(db: Session, user_id: int) -> dict[str, list[dict[str, Any]]]:
    """Return the user's pinboard threads and messages."""
    threads = db.query(PinboardThread).filter(PinboardThread.author_id == user_id).all()
    messages = db.query(PinboardMessage).filter(PinboardMessage.author_id == user_id).all()
    return {
        "threads": [
            {
                "id": t.id,
                "title": t.title,
                "is_pinned": t.is_pinned,
                "created_at": serialize_datetime(t.created_at),
            }
            for t in threads
        ],
        "messages": [
            {
                "id": m.id,
                "thread_id": m.thread_id,
                "content": m.content,
                "created_at": serialize_datetime(m.created_at),
            }
            for m in messages
        ],
    }


def _audit_log_to_dict(a: AuditLog) -> dict[str, Any]:
    return {
        "id": a.id,
        "action": a.action,
        "resource_type": a.resource_type,
        "resource_id": a.resource_id,
        "details": a.details,
        "ip_address": a.ip_address,
        "created_at": serialize_datetime(a.created_at),
    }


def collect_audit_logs(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Return all audit logs touching the user (as actor or as resource).

    De-duplicates by ``id`` and sorts by ``created_at`` ascending so the output
    is stable.
    """
    actor_logs = db.query(AuditLog).filter(AuditLog.user_id == user_id).all()
    resource_logs = (
        db.query(AuditLog).filter(AuditLog.resource_type == "user", AuditLog.resource_id == str(user_id)).all()
    )

    merged: dict[int, dict[str, Any]] = {}
    for a in actor_logs:
        merged[a.id] = _audit_log_to_dict(a)
    for a in resource_logs:
        if a.id not in merged:
            merged[a.id] = _audit_log_to_dict(a)

    return sorted(merged.values(), key=lambda x: x["created_at"] or "")


__all__ = [
    "collect_audit_logs",
    "collect_employee_contracts",
    "collect_employee_shift_wishes",
    "collect_employee_shiftplans",
    "collect_employee_timecards",
    "collect_employees",
    "collect_pinboard",
    "collect_user",
    "serialize_date",
    "serialize_datetime",
]
