"""DSGVO Art. 17 (Right to Erasure) and Art. 20 (Data Portability) service.

The data-export side is split into per-category collectors in
``gdpr_collectors`` to keep each function small and testable. The orchestrator
``export_user_data`` here just calls the collectors in sequence and assembles
the final payload — the output format is byte-identical to the pre-refactor
implementation, so the public API and CSV shape do not change.
"""

import csv
import io
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog
from app.db.models.employee import Contract, Employee, Timecard
from app.db.models.pinboard import PinboardMessage, PinboardThread
from app.db.models.revoked_token import RevokedToken
from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User
from app.services.gdpr_collectors import (
    collect_audit_logs,
    collect_employees,
    collect_pinboard,
    collect_user,
    serialize_datetime,
)


def export_user_data(db: Session, user_id: int) -> dict:
    """Export all personal data associated with a user (DSGVO Art. 20).

    Pipeline:
        1. ``collect_user``  — user profile
        2. ``collect_employees`` — linked employees + nested sub-collections
        3. ``collect_pinboard``  — pinboard threads and messages
        4. ``collect_audit_logs`` — actor + resource audit entries (deduped)

    Returns a JSON-serializable dict.
    """
    user_block = collect_user(db, user_id)
    if user_block is None:
        raise ValueError(f"User {user_id} not found")

    # We need the User ORM object for the linked-employees lookup; the user
    # block already proved it exists, so a fresh query is safe and short.
    user = db.query(User).filter(User.id == user_id).first()
    employees_data = collect_employees(db, user)
    employee_data = employees_data[0] if employees_data else None

    return {
        "export_date": serialize_datetime(datetime.now(timezone.utc)),
        "user": user_block,
        "employee": employee_data,
        "pinboard": collect_pinboard(db, user_id),
        "audit_logs": collect_audit_logs(db, user_id),
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


def _write_csv_section(writer, title: str, rows: list[dict]):
    """Write a named section to the CSV output."""
    writer.writerow([f"# {title}"])
    if rows:
        writer.writerow(rows[0].keys())
        for row in rows:
            writer.writerow(str(v) if v is not None else "" for v in row.values())
    writer.writerow([])


def export_user_data_csv(db: Session, user_id: int) -> str:
    """Export all personal data as CSV (DSGVO Art. 20).

    Returns a multi-section CSV string.
    """
    data = export_user_data(db, user_id)
    output = io.StringIO()
    writer = csv.writer(output)

    # Export date
    writer.writerow(["# EXPORT_DATE"])
    writer.writerow([data.get("export_date", "")])
    writer.writerow([])

    # User
    user = data.get("user")
    if user:
        _write_csv_section(writer, "USER", [user])

    # Employee
    employee = data.get("employee")
    if employee:
        emp_row = {k: v for k, v in employee.items() if not isinstance(v, list)}
        _write_csv_section(writer, "EMPLOYEE", [emp_row])
        _write_csv_section(writer, "CONTRACTS", employee.get("contracts", []))
        _write_csv_section(writer, "TIMECARDS", employee.get("timecards", []))
        _write_csv_section(writer, "SHIFT_WISHES", employee.get("shift_wishes", []))
        _write_csv_section(writer, "SHIFTPLANS", employee.get("shiftplans", []))

    # Pinboard
    pinboard = data.get("pinboard", {})
    _write_csv_section(writer, "PINBOARD_THREADS", pinboard.get("threads", []))
    _write_csv_section(writer, "PINBOARD_MESSAGES", pinboard.get("messages", []))

    # Audit logs
    _write_csv_section(writer, "AUDIT_LOGS", data.get("audit_logs", []))

    return output.getvalue()
