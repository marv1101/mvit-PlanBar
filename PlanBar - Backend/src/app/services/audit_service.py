from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog
from app.schemas.pagination import PaginatedResponse


def log(
    db: Session,
    user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def log_create(
    db: Session,
    user_id: int | None,
    resource_type: str,
    resource_id: str | None = None,
    details: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    return log(
        db,
        user_id=user_id,
        action="CREATE",
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def log_update(
    db: Session,
    user_id: int | None,
    resource_type: str,
    resource_id: str | None = None,
    details: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    return log(
        db,
        user_id=user_id,
        action="UPDATE",
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def log_delete(
    db: Session,
    user_id: int | None,
    resource_type: str,
    resource_id: str | None = None,
    details: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    return log(
        db,
        user_id=user_id,
        action="DELETE",
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def log_access(
    db: Session,
    user_id: int | None,
    resource_type: str,
    resource_id: str | None = None,
    details: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    return log(
        db,
        user_id=user_id,
        action="ACCESS",
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def query(
    db: Session,
    offset: int = 0,
    limit: int = 20,
    user_id: int | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> tuple[list[AuditLog], dict]:
    q = db.query(AuditLog)

    if user_id is not None:
        q = q.filter(AuditLog.user_id == user_id)
    if action is not None:
        q = q.filter(AuditLog.action == action)
    if resource_type is not None:
        q = q.filter(AuditLog.resource_type == resource_type)
    if resource_id is not None:
        q = q.filter(AuditLog.resource_id == resource_id)
    if start_date is not None:
        q = q.filter(AuditLog.created_at >= start_date)
    if end_date is not None:
        q = q.filter(AuditLog.created_at <= end_date)

    total = q.count()
    q = q.order_by(AuditLog.created_at.desc())
    items = q.offset(offset).limit(limit).all()
    pagination = {"total": total, "offset": offset, "limit": limit}
    return items, pagination


def get_suspicious_patterns(db: Session) -> list[dict]:
    patterns = []

    # 1. Multiple failed login attempts from same IP
    five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
    recent_failures = (
        db.query(AuditLog.ip_address, func.count(AuditLog.id).label("cnt"))
        .filter(
            AuditLog.action == "LOGIN_FAILED",
            AuditLog.created_at >= five_min_ago,
        )
        .group_by(AuditLog.ip_address)
        .having(func.count(AuditLog.id) >= 5)
        .all()
    )
    for row in recent_failures:
        logs = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "LOGIN_FAILED",
                AuditLog.ip_address == row.ip_address,
            )
            .order_by(AuditLog.created_at.desc())
            .limit(10)
            .all()
        )
        patterns.append(
            {
                "pattern_type": "brute_force",
                "description": f"Multiple failed logins from IP {row.ip_address}",
                "count": row.cnt,
                "details": logs,
            }
        )

    # 2. Logins for non-existent users
    recent_failures_all = (
        db.query(AuditLog)
        .filter(
            AuditLog.action == "LOGIN_FAILED",
            AuditLog.user_id.is_(None),
        )
        .order_by(AuditLog.created_at.desc())
        .limit(10)
        .all()
    )
    if recent_failures_all:
        patterns.append(
            {
                "pattern_type": "non_existent_user",
                "description": "Login attempts for non-existent or unknown users",
                "count": len(recent_failures_all),
                "details": recent_failures_all,
            }
        )

    # 3. Rapid successive operations by same user (potential scripted access)
    recent_ops = (
        db.query(AuditLog.user_id, func.count(AuditLog.id).label("cnt"))
        .filter(
            AuditLog.created_at >= five_min_ago,
            AuditLog.user_id.isnot(None),
        )
        .group_by(AuditLog.user_id)
        .having(func.count(AuditLog.id) >= 50)
        .all()
    )
    for row in recent_ops:
        logs = (
            db.query(AuditLog)
            .filter(
                AuditLog.user_id == row.user_id,
                AuditLog.created_at >= five_min_ago,
            )
            .order_by(AuditLog.created_at.desc())
            .limit(10)
            .all()
        )
        patterns.append(
            {
                "pattern_type": "rapid_operations",
                "description": f"High volume of operations by user {row.user_id} in last 5 minutes",
                "count": row.cnt,
                "details": logs,
            }
        )

    return patterns
