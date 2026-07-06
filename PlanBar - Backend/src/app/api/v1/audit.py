import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_admin
from app.db.models.user import User
from app.schemas.audit import (
    AuditLogListResponse,
    AuditLogResponse,
    SuspiciousPatternResponse,
)
from app.services import audit_service

router = APIRouter()


def _csv_escape(value: str | None) -> str:
    if value is None:
        return ""
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


@router.get("/audit-logs/suspicious", response_model=list[SuspiciousPatternResponse])
def get_suspicious_patterns(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return audit_service.get_suspicious_patterns(db)


@router.get("/audit-logs/export")
def export_audit_logs(
    action: str | None = None,
    resource_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    items, _ = audit_service.query(
        db,
        offset=0,
        limit=10000,
        action=action,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID",
            "User ID",
            "Action",
            "Resource Type",
            "Resource ID",
            "Details",
            "IP Address",
            "User Agent",
            "Created At",
        ]
    )
    for entry in items:
        writer.writerow(
            [
                entry.id,
                entry.user_id,
                entry.action,
                entry.resource_type,
                _csv_escape(entry.resource_id),
                _csv_escape(entry.details),
                _csv_escape(entry.ip_address),
                _csv_escape(entry.user_agent),
                entry.created_at.isoformat(),
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )


@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    user_id: int | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    items, pagination = audit_service.query(
        db,
        offset=offset,
        limit=limit,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        start_date=start_date,
        end_date=end_date,
    )
    return {"items": items, "total": pagination["total"], "offset": pagination["offset"], "limit": pagination["limit"]}


@router.get("/audit-logs/{log_id}", response_model=AuditLogResponse)
def get_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    entry = db.query(audit_service.AuditLog).filter(audit_service.AuditLog.id == log_id).first()
    if not entry:
        from app.core.exceptions import NotFoundException

        raise NotFoundException(detail="Audit log entry not found")
    return entry
