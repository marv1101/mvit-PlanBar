"""DSGVO Aufbewahrungsfristen — Retention Service (Issue #48).

Zentrale Implementierung der automatischen Datenbereinigung gemäß
Art. 5 Abs. 1 lit. e DSGVO (Speicherbegrenzung).

Rechtsgrundlagen und Fristen: Docs/dsgvo/aufbewahrungsfristen.md
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog
from app.db.models.employee import Employee, Timecard
from app.db.models.pinboard import PinboardMessage, PinboardThread
from app.db.models.retention_audit import RetentionAuditLog
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.shift_swap import ShiftSwapRequest
from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User


def _uuid8() -> str:
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Retention Rules
# ---------------------------------------------------------------------------
# Quelle: Docs/dsgvo/aufbewahrungsfristen.md
#
# Jede Regel definiert:
#   category     — eindeutiger Bezeichner (→ retention_audit_logs.category)
#   description  — Menschenlesbar
#   retention_days — Aufbewahrungsfrist in Tagen
#   action       — "delete" | "pseudonymize"
#   table        — DB-Tabellenname (für Information; Cleanup nutzt ORM)
#   legal_basis  — Rechtsgrundlage Kurzform

RETENTION_RULES: dict[str, dict] = {
    "user_inactive": {
        "category": "user",
        "description": "User-Account (inaktiv) — 6 Monate nach letzter Aktivität",
        "retention_days": 180,
        "action": "pseudonymize",
        "table": "users",
        "legal_basis": "Beweissicherung",
    },
    "employee_separated": {
        "category": "employee",
        "description": "Employee-Stammdaten (ausgeschieden) — 10 Jahre",
        "retention_days": 3650,
        "action": "pseudonymize",
        "table": "employees",
        "legal_basis": "§ 147 AO",
    },
    "timecards": {
        "category": "timecard",
        "description": "Zeitkonto-Daten — 10 Jahre",
        "retention_days": 3650,
        "action": "delete",
        "table": "timecards",
        "legal_basis": "§ 147 AO, Lohnunterlagen",
    },
    "auth_logs": {
        "category": "auth_log",
        "description": "Auth-Logs (Login/Logout) — 1 Jahr",
        "retention_days": 365,
        "action": "delete",
        "table": "audit_logs",
        "legal_basis": "Sicherheits-Compliance",
    },
    "audit_logs": {
        "category": "audit_log",
        "description": "Audit-Logs — 3 Jahre",
        "retention_days": 1095,
        "action": "delete",
        "table": "audit_logs",
        "legal_basis": "Art. 30 DSGVO Nachweis",
    },
    "schedules_completed": {
        "category": "schedule",
        "description": "Schichtpläne (abgeschlossen) — 2 Jahre",
        "retention_days": 730,
        "action": "delete",
        "table": "schedules",
        "legal_basis": "Betrieblich",
    },
    "shift_wishes_processed": {
        "category": "shift_wish",
        "description": "Schichtwünsche (verarbeitet) — 1 Jahr",
        "retention_days": 365,
        "action": "delete",
        "table": "shift_wishes",
        "legal_basis": "Betrieblich",
    },
    "vacation_requests": {
        "category": "shift_wish",
        "description": "Urlaubsanträge (abgeschlossen) — 5 Jahre",
        "retention_days": 1825,
        "action": "delete",
        "table": "shift_wishes",
        "legal_basis": "Urlaubsrecht",
    },
    "pinboard_entries": {
        "category": "pinboard",
        "description": "Pinboard-Einträge — 1 Jahr nach letzter Aktivität",
        "retention_days": 365,
        "action": "delete",
        "table": "pinboard_threads",
        "legal_basis": "Betrieblich",
    },
    "shift_swap_requests": {
        "category": "shift_swap",
        "description": "Schichttausch-Anfragen (verarbeitet) — 1 Jahr",
        "retention_days": 365,
        "action": "delete",
        "table": "shift_swap_requests",
        "legal_basis": "Betrieblich",
    },
}


# ---------------------------------------------------------------------------
# Audit-Trail
# ---------------------------------------------------------------------------

def _write_audit(
    db: Session,
    category: str,
    action: str,
    record_id: str,
    reason: str,
    executed_by: str = "system",
) -> RetentionAuditLog:
    entry = RetentionAuditLog(
        id=str(uuid.uuid4()),
        category=category,
        action=action,
        record_id=record_id,
        reason=reason,
        executed_at=datetime.now(timezone.utc),
        executed_by=executed_by,
    )
    db.add(entry)
    return entry


# ---------------------------------------------------------------------------
# Pseudonymisierung
# ---------------------------------------------------------------------------

def _pseudonymize_user(user: User, db: Session, executed_by: str = "system") -> None:
    tag = _uuid8()
    pseudonym = f"[GELÖSCHT-{tag}]"
    user.username = pseudonym
    user.email = f"deleted-{tag}@deleted.local"
    user.password_hash = "DELETED"
    user.role = "user"
    user.must_change_password = False
    user.last_login = None
    user.processing_restricted = False
    user.objection_filed = False
    user.objection_date = None
    db.add(user)
    _write_audit(
        db,
        category="user",
        action="pseudonymized",
        record_id=tag,
        reason="retention_policy_6_months",
        executed_by=executed_by,
    )


def _pseudonymize_employee(employee: Employee, db: Session, executed_by: str = "system") -> None:
    tag = _uuid8()
    pseudonym = f"[GELÖSCHT-{tag}]"
    employee.first_name = "Gelöscht"
    employee.last_name = pseudonym
    employee.email = f"deleted-{tag}@deleted.local"
    employee.color = "#999999"
    employee.user_id = None
    employee.processing_restricted = False
    db.add(employee)
    _write_audit(
        db,
        category="employee",
        action="pseudonymized",
        record_id=tag,
        reason="retention_policy_10_years",
        executed_by=executed_by,
    )


def _delete_record(record, db: Session) -> None:
    db.delete(record)


# ---------------------------------------------------------------------------
# Cleanup-Funktionen je Kategorie
# ---------------------------------------------------------------------------

def _cleanup_users(db: Session, now: datetime, dry_run: bool) -> dict:
    cutoff = now - timedelta(days=RETENTION_RULES["user_inactive"]["retention_days"])
    inactive_users = (
        db.query(User)
        .filter(
            User.last_login.isnot(None),
            User.last_login < cutoff,
        )
        .all()
    )
    pseudonymized = 0
    for user in inactive_users:
        if not dry_run:
            _pseudonymize_user(user, db)
        pseudonymized += 1
    return {"pseudonymized": pseudonymized, "deleted": 0}


def _cleanup_employees(db: Session, now: datetime, dry_run: bool) -> dict:
    cutoff = now - timedelta(days=RETENTION_RULES["employee_separated"]["retention_days"])
    separated_employees = (
        db.query(Employee)
        .filter(
            Employee.user_id.is_(None),
            Employee.updated_at < cutoff,
        )
        .all()
    )
    pseudonymized = 0
    for emp in separated_employees:
        if not dry_run:
            _pseudonymize_employee(emp, db)
        pseudonymized += 1
    return {"pseudonymized": pseudonymized, "deleted": 0}


def _cleanup_timecards(db: Session, now: datetime, dry_run: bool) -> dict:
    cutoff = now - timedelta(days=RETENTION_RULES["timecards"]["retention_days"])
    old_timecards = db.query(Timecard).filter(Timecard.created_at < cutoff).all()
    deleted = 0
    for tc in old_timecards:
        if not dry_run:
            _write_audit(
                db,
                category="timecard",
                action="deleted",
                record_id=str(tc.id),
                reason="retention_policy_10_years",
            )
            _delete_record(tc, db)
        deleted += 1
    return {"pseudonymized": 0, "deleted": deleted}


def _cleanup_auth_logs(db: Session, now: datetime, dry_run: bool) -> dict:
    cutoff = now - timedelta(days=RETENTION_RULES["auth_logs"]["retention_days"])
    auth_actions = ("LOGIN_SUCCESS", "LOGIN_FAILED", "LOGOUT")
    old_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.action.in_(auth_actions),
            AuditLog.created_at < cutoff,
        )
        .all()
    )
    deleted = 0
    for log_entry in old_logs:
        if not dry_run:
            _write_audit(
                db,
                category="auth_log",
                action="deleted",
                record_id=str(log_entry.id),
                reason="retention_policy_1_year",
            )
            _delete_record(log_entry, db)
        deleted += 1
    return {"pseudonymized": 0, "deleted": deleted}


def _cleanup_audit_logs(db: Session, now: datetime, dry_run: bool) -> dict:
    cutoff = now - timedelta(days=RETENTION_RULES["audit_logs"]["retention_days"])
    # Exclude auth logs (already handled by _cleanup_auth_logs)
    auth_actions = ("LOGIN_SUCCESS", "LOGIN_FAILED", "LOGOUT")
    old_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.action.notin_(auth_actions),
            AuditLog.created_at < cutoff,
        )
        .all()
    )
    deleted = 0
    for log_entry in old_logs:
        if not dry_run:
            _write_audit(
                db,
                category="audit_log",
                action="deleted",
                record_id=str(log_entry.id),
                reason="retention_policy_3_years",
            )
            _delete_record(log_entry, db)
        deleted += 1
    return {"pseudonymized": 0, "deleted": deleted}


def _cleanup_schedules(db: Session, now: datetime, dry_run: bool) -> dict:
    cutoff = now - timedelta(days=RETENTION_RULES["schedules_completed"]["retention_days"])
    old_schedules = (
        db.query(Schedule)
        .filter(
            Schedule.end_date.isnot(None),
            Schedule.end_date < cutoff.date(),
        )
        .all()
    )
    deleted = 0
    for schedule in old_schedules:
        if not dry_run:
            # Delete associated shiftplans first
            db.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).delete()
            _write_audit(
                db,
                category="schedule",
                action="deleted",
                record_id=str(schedule.id),
                reason="retention_policy_2_years",
            )
            _delete_record(schedule, db)
        deleted += 1
    return {"pseudonymized": 0, "deleted": deleted}


def _cleanup_shift_wishes(db: Session, now: datetime, dry_run: bool) -> dict:
    processed = ("approved", "rejected")
    # 1 year retention for general shift wishes
    cutoff_1y = now - timedelta(days=RETENTION_RULES["shift_wishes_processed"]["retention_days"])
    # 5 year retention for vacation requests
    cutoff_5y = now - timedelta(days=RETENTION_RULES["vacation_requests"]["retention_days"])

    deleted = 0
    # Delete non-vacation processed wishes older than 1 year
    old_wishes = (
        db.query(ShiftWish)
        .filter(
            ShiftWish.status.in_(processed),
            ShiftWish.type != "vacation",
            ShiftWish.updated_at < cutoff_1y,
        )
        .all()
    )
    for wish in old_wishes:
        if not dry_run:
            _write_audit(
                db,
                category="shift_wish",
                action="deleted",
                record_id=str(wish.id),
                reason="retention_policy_1_year",
            )
            _delete_record(wish, db)
        deleted += 1

    # Delete vacation requests older than 5 years
    old_vacation = (
        db.query(ShiftWish)
        .filter(
            ShiftWish.status.in_(processed),
            ShiftWish.type == "vacation",
            ShiftWish.updated_at < cutoff_5y,
        )
        .all()
    )
    for wish in old_vacation:
        if not dry_run:
            _write_audit(
                db,
                category="shift_wish",
                action="deleted",
                record_id=str(wish.id),
                reason="retention_policy_5_years",
            )
            _delete_record(wish, db)
        deleted += 1

    return {"pseudonymized": 0, "deleted": deleted}


def _cleanup_pinboard(db: Session, now: datetime, dry_run: bool) -> dict:
    cutoff = now - timedelta(days=RETENTION_RULES["pinboard_entries"]["retention_days"])
    old_threads = db.query(PinboardThread).filter(PinboardThread.updated_at < cutoff).all()
    deleted = 0
    for thread in old_threads:
        if not dry_run:
            # Delete messages first (cascade should handle, but be explicit)
            db.query(PinboardMessage).filter(PinboardMessage.thread_id == thread.id).delete()
            _write_audit(
                db,
                category="pinboard",
                action="deleted",
                record_id=str(thread.id),
                reason="retention_policy_1_year",
            )
            _delete_record(thread, db)
        deleted += 1
    return {"pseudonymized": 0, "deleted": deleted}


def _cleanup_shift_swaps(db: Session, now: datetime, dry_run: bool) -> dict:
    cutoff = now - timedelta(days=RETENTION_RULES["shift_swap_requests"]["retention_days"])
    processed = ("approved", "rejected")
    old_swaps = (
        db.query(ShiftSwapRequest)
        .filter(
            ShiftSwapRequest.status.in_(processed),
            ShiftSwapRequest.updated_at < cutoff,
        )
        .all()
    )
    deleted = 0
    for swap in old_swaps:
        if not dry_run:
            _write_audit(
                db,
                category="shift_swap",
                action="deleted",
                record_id=str(swap.id),
                reason="retention_policy_1_year",
            )
            _delete_record(swap, db)
        deleted += 1
    return {"pseudonymized": 0, "deleted": deleted}


# ---------------------------------------------------------------------------
# Hauptfunktion
# ---------------------------------------------------------------------------

_CLEANUP_DISPATCH: list[tuple[str, callable]] = [
    ("user", _cleanup_users),
    ("employee", _cleanup_employees),
    ("timecard", _cleanup_timecards),
    ("auth_log", _cleanup_auth_logs),
    ("audit_log", _cleanup_audit_logs),
    ("schedule", _cleanup_schedules),
    ("shift_wish", _cleanup_shift_wishes),
    ("pinboard", _cleanup_pinboard),
    ("shift_swap", _cleanup_shift_swaps),
]


def cleanup_expired_data(db: Session, dry_run: bool = False, executed_by: str = "system") -> dict:
    """Prüft alle Retention-Rules und bereinigt abgelaufene Daten.

    Args:
        db: SQLAlchemy Session
        dry_run: Wenn True, werden keine Änderungen vorgenommen
        executed_by: Identität des Ausführenden ("system" oder Admin-Username)

    Returns:
        dict mit je Kategorie: {"pseudonymized": int, "deleted": int}
    """
    now = datetime.now(timezone.utc)
    report: dict[str, dict] = {}

    for category, cleanup_fn in _CLEANUP_DISPATCH:
        result = cleanup_fn(db, now, dry_run)
        if result["pseudonymized"] > 0 or result["deleted"] > 0:
            report[category] = result

    if not dry_run:
        db.commit()

    return report


def get_policies() -> list[dict]:
    """Gibt alle aktiven Retention-Regeln zurück."""
    return [
        {
            "key": key,
            "category": rule["category"],
            "description": rule["description"],
            "retention_days": rule["retention_days"],
            "action": rule["action"],
            "table": rule["table"],
            "legal_basis": rule["legal_basis"],
        }
        for key, rule in RETENTION_RULES.items()
    ]
