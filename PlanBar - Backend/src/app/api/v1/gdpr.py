"""DSGVO Art. 17 (Right to Erasure) and Art. 20 (Data Portability) endpoints.

GET  /api/v1/gdpr/export  — Export current user's personal data (Art. 20)
DELETE /api/v1/gdpr/account — Delete/anonymize current user's account (Art. 17)
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.db.models.user import User
from app.services import audit_service
from app.services.gdpr_service import delete_user_data, export_user_data

router = APIRouter()


@router.get("/export")
def export_my_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export all personal data for the authenticated user (DSGVO Art. 20)."""
    data = export_user_data(db, current_user.id)

    audit_service.log_access(
        db,
        user_id=current_user.id,
        resource_type="user",
        resource_id=str(current_user.id),
        details="DSGVO Art. 20 data export",
    )

    return data


@router.delete("/account", status_code=status.HTTP_200_OK)
def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete/anonymize the authenticated user's account and personal data (DSGVO Art. 17).

    This anonymizes personal data while preserving schedule structure.
    The user account itself is hard-deleted after anonymization.
    """
    user_id = current_user.id
    user_email = current_user.email

    # Log the GDPR deletion request BEFORE deleting
    audit_service.log_delete(
        db,
        user_id=user_id,
        resource_type="user",
        resource_id=str(user_id),
        details=f"DSGVO Art. 17 account deletion requested by user {user_email}",
    )

    summary = delete_user_data(db, user_id)

    return {
        "message": "Account and personal data have been deleted/anonymized per DSGVO Art. 17.",
        "details": summary,
    }
