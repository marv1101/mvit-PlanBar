"""DSGVO Aufbewahrungsfristen — Admin-Endpoints (Issue #48).

POST   /api/v1/retention/cleanup   — Manueller Trigger, gibt Report zurück
GET    /api/v1/retention/policies  — Liste der aktiven Regeln
GET    /api/v1/retention/preview   — Dry-Run, zeigt was gelöscht würde
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_admin
from app.db.models.user import User
from app.services.retention_service import cleanup_expired_data, get_policies

router = APIRouter()


@router.post("/cleanup")
def trigger_cleanup(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    report = cleanup_expired_data(db, dry_run=False, executed_by=admin.username)
    return {
        "message": "Retention cleanup completed",
        "executed_by": admin.username,
        "report": report,
    }


@router.get("/policies")
def list_policies(
    admin: User = Depends(require_admin),
):
    return {"policies": get_policies()}


@router.get("/preview")
def preview_cleanup(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    report = cleanup_expired_data(db, dry_run=True, executed_by=admin.username)
    return {
        "message": "Dry-run preview (no changes made)",
        "report": report,
    }
