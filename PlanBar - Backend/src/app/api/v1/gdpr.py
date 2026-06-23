"""DSGVO Art. 17 (Right to Erasure) and Art. 20 (Data Portability) endpoints.

GET  /api/v1/gdpr/export                — Export current user's personal data (Art. 20)
GET  /api/v1/admin/employees/{id}/export — Admin export of any employee's data (Art. 20)
DELETE /api/v1/gdpr/account             — Delete/anonymize current user's account (Art. 17)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_admin
from app.db.models.employee import Employee
from app.db.models.user import User
from app.services import audit_service
from app.services.gdpr_service import delete_user_data, export_user_data, export_user_data_csv

router = APIRouter()


@router.get("/export")
def export_my_data(
    format: str = Query("json", pattern="^(json|csv)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export all personal data for the authenticated user (DSGVO Art. 20)."""
    audit_service.log_access(
        db,
        user_id=current_user.id,
        resource_type="user",
        resource_id=str(current_user.id),
        details="DSGVO Art. 20 data export",
    )

    if format == "csv":
        csv_content = export_user_data_csv(db, current_user.id)
        return Response(
            content=csv_content,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="gdpr_export_user_{current_user.id}.csv"'
            },
        )

    data = export_user_data(db, current_user.id)
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="gdpr_export_user_{current_user.id}.json"'
        },
    )


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


admin_router = APIRouter()


@admin_router.get("/employees/{employee_id}/export")
def admin_export_employee_data(
    employee_id: int,
    format: str = Query("json", pattern="^(json|csv)$"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: Export all personal data for a specific employee (DSGVO Art. 20)."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    user_id = employee.user_id
    if user_id is None:
        raise HTTPException(status_code=404, detail="No user linked to this employee")

    audit_service.log_access(
        db,
        user_id=admin.id,
        resource_type="employee",
        resource_id=str(employee_id),
        details=f"DSGVO Art. 20 admin data export for employee {employee_id}",
    )

    if format == "csv":
        csv_content = export_user_data_csv(db, user_id)
        return Response(
            content=csv_content,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="gdpr_export_employee_{employee_id}.csv"'
            },
        )

    data = export_user_data(db, user_id)
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="gdpr_export_employee_{employee_id}.json"'
        },
    )
