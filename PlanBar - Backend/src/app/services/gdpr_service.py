"""DSGVO Art. 17 (Right to Erasure) and Art. 20 (Data Portability) service.

Provides functions to export all user-related data and to anonymize/delete
user data in compliance with GDPR requirements.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog
from app.db.models.employee import Contract, Employee, Timecard
from app.db.models.pinboard import PinboardMessage, PinboardThread
from app.db.models.revoked_token import RevokedToken
from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User


def _serialize_datetime(dt):
    """Convert a datetime to ISO format string for JSON serialization."""
    if dt is None:
        return None
    return dt.isoformat()


def _serialize_date(d):
    """Convert a date to ISO format string for JSON serialization."""
    if d is None:
        return None
    return d.isoformat()


def export_user_data(db: Session, user_id: int) -> dict:
    """Export all personal data associated with a user (DSGVO Art. 20).

    Returns a JSON-serializable dict containing:
    - User profile
    - Linked employee data (if any)
    - Contracts, timecards, shift wishes
    - Shiftplans referencing the employee
    - Pinboard threads and messages authored by user
    - Audit log entries related to the user
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise ValueError(f"User {user_id} not found")

    # --- User profile ---
    user_data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "must_change_password": user.must_change_password,
        "created_at": _serialize_datetime(user.created_at),
        "updated_at": _serialize_datetime(user.updated_at),
        "last_login": _serialize_datetime(user.last_login),
    }

    # --- Linked employees (may be multiple) ---
    employees_list = db.query(Employee).filter(Employee.user_id == user_id).all()
    if user.employee_id is not None:
        extra = db.query(Employee).filter(Employee.id == user.employee_id).first()
        if extra is not None and extra not in employees_list:
            employees_list.append(extra)

    employees_data = []
    from app.db.models.schedule import Shiftplan as ShiftplanModel

    for employee in employees_list:
        contracts = [
            {
                "id": c.id,
                "weekly_working_hours": c.weekly_working_hours,
                "break_time": c.break_time,
                "hired_role": c.hired_role,
                "created_at": _serialize_datetime(c.created_at),
                "updated_at": _serialize_datetime(c.updated_at),
            }
            for c in employee.contracts
        ]

        timecards = [
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
                "created_at": _serialize_datetime(t.created_at),
                "updated_at": _serialize_datetime(t.updated_at),
            }
            for t in employee.timecards
        ]

        shift_wishes = [
            {
                "id": sw.id,
                "date": _serialize_date(sw.date),
                "week": sw.week,
                "type": sw.type,
                "note": sw.note,
                "status": sw.status,
                "reviewed_by": sw.reviewed_by,
                "reviewed_at": _serialize_datetime(sw.reviewed_at),
                "rejection_reason": sw.rejection_reason,
                "created_at": _serialize_datetime(sw.created_at),
                "updated_at": _serialize_datetime(sw.updated_at),
            }
            for sw in employee.shift_wishes
        ]

        shiftplan_rows = db.query(ShiftplanModel).filter(ShiftplanModel.employee_id == employee.id).all()
        shiftplans_data = [
            {
                "id": sp.id,
                "schedule_id": sp.schedule_id,
                "date": _serialize_date(sp.date),
                "shift_id": sp.shift_id,
                "start_time": sp.start_time.isoformat() if sp.start_time else None,
                "end_time": sp.end_time.isoformat() if sp.end_time else None,
                "label": sp.label,
                "notes": sp.notes,
                "created_at": _serialize_datetime(sp.created_at),
            }
            for sp in shiftplan_rows
        ]

        employees_data.append(
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
                "created_at": _serialize_datetime(employee.created_at),
                "updated_at": _serialize_datetime(employee.updated_at),
                "contracts": contracts,
                "timecards": timecards,
                "shift_wishes": shift_wishes,
                "shiftplans": shiftplans_data,
            }
        )

    # Backward compat: return first employee as "employee" if only one
    employee_data = employees_data[0] if employees_data else None

    # --- Pinboard ---
    threads = db.query(PinboardThread).filter(PinboardThread.author_id == user_id).all()
    threads_data = [
        {
            "id": t.id,
            "title": t.title,
            "is_pinned": t.is_pinned,
            "created_at": _serialize_datetime(t.created_at),
        }
        for t in threads
    ]

    messages = db.query(PinboardMessage).filter(PinboardMessage.author_id == user_id).all()
    messages_data = [
        {
            "id": m.id,
            "thread_id": m.thread_id,
            "content": m.content,
            "created_at": _serialize_datetime(m.created_at),
        }
        for m in messages
    ]

    # --- Audit logs ---
    audit_logs = db.query(AuditLog).filter(AuditLog.user_id == user_id).all()
    audit_data = [
        {
            "id": a.id,
            "action": a.action,
            "resource_type": a.resource_type,
            "resource_id": a.resource_id,
            "details": a.details,
            "ip_address": a.ip_address,
            "created_at": _serialize_datetime(a.created_at),
        }
        for a in audit_logs
    ]

    # --- Also include audit logs where this user was the resource ---
    resource_audit_logs = (
        db.query(AuditLog).filter(AuditLog.resource_type == "user", AuditLog.resource_id == str(user_id)).all()
    )
    resource_audit_data = [
        {
            "id": a.id,
            "action": a.action,
            "resource_type": a.resource_type,
            "resource_id": a.resource_id,
            "details": a.details,
            "ip_address": a.ip_address,
            "created_at": _serialize_datetime(a.created_at),
        }
        for a in resource_audit_logs
    ]

    # Merge audit logs (deduplicate by id)
    all_audit = {a["id"]: a for a in audit_data}
    for a in resource_audit_data:
        if a["id"] not in all_audit:
            all_audit[a["id"]] = a

    return {
        "export_date": _serialize_datetime(datetime.now(timezone.utc)),
        "user": user_data,
        "employee": employee_data,
        "pinboard": {
            "threads": threads_data,
            "messages": messages_data,
        },
        "audit_logs": sorted(all_audit.values(), key=lambda x: x["created_at"] or ""),
    }


def delete_user_data(db: Session, user_id: int) -> dict:
    """Anonymize all personal data for a user (DSGVO Art. 17).

    Rather than hard-deleting (which would break schedule structure and
    cascade through foreign keys), we anonymize personal fields while
    preserving operational data.

    Returns a summary of what was anonymized.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise ValueError(f"User {user_id} not found")

    anonymized_id = f"anonymized_{uuid.uuid4().hex[:8]}"
    summary = {
        "user_id": user_id,
        "anonymized_id": anonymized_id,
        "anonymized_at": datetime.now(timezone.utc).isoformat(),
        "actions": [],
    }

    # 1. Anonymize user account
    user.username = anonymized_id
    user.email = f"{anonymized_id}@deleted.invalid"
    user.password_hash = "DELETED"
    user.role = "user"
    user.must_change_password = False
    user.last_login = None
    db.add(user)
    summary["actions"].append("user_anonymized")

    # 2. Anonymize ALL linked employees (if any)
    employees = db.query(Employee).filter(Employee.user_id == user_id).all()
    # Also check by user.employee_id if set
    if user.employee_id is not None:
        extra = db.query(Employee).filter(Employee.id == user.employee_id).first()
        if extra is not None and extra not in employees:
            employees.append(extra)

    for employee in employees:
        employee.first_name = "Gelöschter"
        employee.last_name = f"Mitarbeiter_{anonymized_id}"
        employee.email = f"{anonymized_id}@deleted.invalid"
        employee.color = "#999999"
        employee.user_id = None
        db.add(employee)
        summary["actions"].append(f"employee_{employee.id}_anonymized")

        # Delete contracts (purely personal employment data)
        db.query(Contract).filter(Contract.employee_id == employee.id).delete()
        summary["actions"].append(f"contracts_deleted_{employee.id}")

        # Delete timecards (personal work time data)
        db.query(Timecard).filter(Timecard.employee_id == employee.id).delete()
        summary["actions"].append(f"timecards_deleted_{employee.id}")

        # Delete shift wishes
        db.query(ShiftWish).filter(ShiftWish.employee_id == employee.id).delete()
        summary["actions"].append(f"shift_wishes_deleted_{employee.id}")

        # Delete shiftplans referencing this employee
        from app.db.models.schedule import Shiftplan as ShiftplanModel

        db.query(ShiftplanModel).filter(ShiftplanModel.employee_id == employee.id).delete()
        summary["actions"].append(f"shiftplans_deleted_{employee.id}")

    # 3. Anonymize pinboard messages authored by user
    msg_count = (
        db.query(PinboardMessage)
        .filter(PinboardMessage.author_id == user_id)
        .update({"content": "[Gelöscht gemäß DSGVO Art. 17]", "author_id": 0})
    )
    summary["actions"].append(f"pinboard_messages_anonymized:{msg_count}")

    # 4. Handle threads authored by user - set author to 0
    thread_count = db.query(PinboardThread).filter(PinboardThread.author_id == user_id).update({"author_id": 0})
    summary["actions"].append(f"pinboard_threads_unlinked:{thread_count}")

    # 5. Anonymize audit logs - set user_id to NULL (model has ondelete=SET NULL)
    db.query(AuditLog).filter(AuditLog.user_id == user_id).update(
        {"user_id": None, "details": "[Gelöscht gemäß DSGVO]"}
    )
    summary["actions"].append("audit_logs_anonymized")

    # 6. Delete revoked tokens
    db.query(RevokedToken).filter(RevokedToken.user_id == user_id).delete()
    summary["actions"].append("revoked_tokens_deleted")

    # 7. Hard delete the user record itself
    db.delete(user)
    summary["actions"].append("user_deleted")

    db.commit()

    return summary
