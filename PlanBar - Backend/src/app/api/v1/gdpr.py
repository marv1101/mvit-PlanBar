"""DSGVO Betroffenenrechte (Art. 15-22) endpoints.

GET    /api/v1/gdpr/export                        — Export current user's data (Art. 20)
GET    /api/v1/gdpr/access                        — Full data access report (Art. 15)
POST   /api/v1/gdpr/restrict-processing           — Restrict own data processing (Art. 18)
POST   /api/v1/gdpr/object                        — Object to data processing (Art. 21)
GET    /api/v1/gdpr/automated-decisions            — Info on automated decisions (Art. 22)
DELETE /api/v1/gdpr/account                       — Delete/anonymize account (Art. 17)
GET    /api/v1/admin/employees/{id}/export         — Admin export (Art. 20)
POST   /api/v1/admin/employees/{id}/restrict-processing — Admin restrict processing (Art. 18)
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_admin
from app.db.models.employee import Employee
from app.db.models.user import User
from app.schemas.gdpr import (
    AutomatedDecisionInfo,
    DataAccessResponse,
    ObjectionResponse,
    ProcessingRestrictionResponse,
)
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
            headers={"Content-Disposition": f'attachment; filename="gdpr_export_user_{current_user.id}.csv"'},
        )

    data = export_user_data(db, current_user.id)
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": f'attachment; filename="gdpr_export_user_{current_user.id}.json"'},
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


@router.get("/access", response_model=DataAccessResponse)
def data_access(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Provide full data access report (DSGVO Art. 15).

    Returns all personal data, processing purposes, recipients,
    retention periods, and a summary of the data subject's rights.
    """
    audit_service.log_access(
        db,
        user_id=current_user.id,
        resource_type="user",
        resource_id=str(current_user.id),
        details="DSGVO Art. 15 data access request",
    )

    employee_data = None
    if current_user.employee_id:
        emp = db.query(Employee).filter(Employee.id == current_user.employee_id).first()
        if emp:
            employee_data = {
                "id": emp.id,
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "email": emp.email,
                "color": emp.color,
                "working_hours_json": emp.working_hours_json,
                "break_start": emp.break_start,
                "break_end": emp.break_end,
                "max_work_hours": emp.max_work_hours,
                "processing_restricted": emp.processing_restricted,
            }

    personal_data = {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "role": current_user.role,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None,
            "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
            "processing_restricted": current_user.processing_restricted,
            "objection_filed": current_user.objection_filed,
            "objection_date": current_user.objection_date.isoformat() if current_user.objection_date else None,
        },
        "employee": employee_data,
    }

    return DataAccessResponse(
        personal_data=personal_data,
        processing_purposes=[
            "Personalverwaltung (employee administration)",
            "Dienstplanerstellung (shift schedule creation)",
            "Zeiterfassung (time tracking)",
            "Gehaltsabrechnung (payroll processing)",
            "Authentifizierung & Zugriffskontrolle (authentication & access control)",
            "Kommunikation & Benachrichtigungen (communication & notifications)",
        ],
        data_recipients=[
            "Interne Administratoren (internal administrators)",
            "Vorgesetzte / Teamleiter (supervisors / team leaders)",
            "Externe Dienstleister im Rahmen der Auftragsverarbeitung (external processors)",
        ],
        retention_periods={
            "account_data": "until account deletion (§ 17) or legal retention period",
            "employee_data": "duration of employment + statutory retention (max. 10 years)",
            "timecard_data": "6 years (§ 257 HGB, § 147 AO)",
            "audit_logs": "3 years (§ 195 BGB)",
            "contract_data": "6 years after end of contract (§ 257 HGB, § 147 AO)",
        },
        rights=[
            "Art. 15: Recht auf Auskunft (right to access)",
            "Art. 16: Recht auf Berichtigung (right to rectification)",
            "Art. 17: Recht auf Löschung (right to erasure)",
            "Art. 18: Recht auf Einschränkung der Verarbeitung (right to restrict processing)",
            "Art. 20: Recht auf Datenübertragbarkeit (right to data portability)",
            "Art. 21: Widerspruchsrecht (right to object)",
            "Art. 22: Recht auf automatische Entscheidungen (right re automated decisions)",
            "Art. 77: Beschwerde bei Aufsichtsbehörde (right to lodge complaint with supervisory authority)",
        ],
    )


@router.post("/restrict-processing", response_model=ProcessingRestrictionResponse)
def restrict_processing(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Restrict processing of own personal data (DSGVO Art. 18).

    Toggles the processing restriction flag for the current user
    and their linked employee record.
    """
    current_user.processing_restricted = not current_user.processing_restricted
    db.add(current_user)
    db.flush()

    if current_user.employee_id:
        emp = db.query(Employee).filter(Employee.id == current_user.employee_id).first()
        if emp:
            emp.processing_restricted = current_user.processing_restricted
            db.add(emp)
            db.flush()

    db.commit()
    db.refresh(current_user)

    action = "restricted" if current_user.processing_restricted else "unrestricted"
    audit_service.log(
        db,
        user_id=current_user.id,
        action="GDPR_RESTRICT_PROCESSING",
        resource_type="user",
        resource_id=str(current_user.id),
        details=f"DSGVO Art. 18: processing {action}",
    )

    return ProcessingRestrictionResponse(
        message=f"Processing has been {action}.",
        restricted=current_user.processing_restricted,
    )


@router.post("/object", response_model=ObjectionResponse)
def object_to_processing(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """File an objection against data processing (DSGVO Art. 21).

    Records the objection and flags the user account accordingly.
    Further processing requires compelling legitimate grounds or
    legal claims.
    """
    current_user.objection_filed = True
    current_user.objection_date = datetime.now(timezone.utc)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    audit_service.log(
        db,
        user_id=current_user.id,
        action="GDPR_OBJECTION",
        resource_type="user",
        resource_id=str(current_user.id),
        details="DSGVO Art. 21: objection to data processing filed",
    )

    return ObjectionResponse(
        message="Objection to data processing has been filed (DSGVO Art. 21).",
        objection_filed=current_user.objection_filed,
        objection_date=current_user.objection_date,
    )


@router.get("/automated-decisions", response_model=AutomatedDecisionInfo)
def automated_decisions_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Provide information about automated decision-making (DSGVO Art. 22).

    Discloses whether automated individual decision-making (including
    profiling) is used and explains the logic, significance, and
    consequences.
    """
    audit_service.log_access(
        db,
        user_id=current_user.id,
        resource_type="user",
        resource_id=str(current_user.id),
        details="DSGVO Art. 22 automated decision info request",
    )

    return AutomatedDecisionInfo(
        automated_decisions_used=False,
        details={
            "status": "PlanBar does not use automated individual decision-making "
            "or profiling that produces legal effects (Art. 22). "
            "All scheduling decisions are reviewed by human administrators.",
            "algorithms_used": [],
            "logic_involved": None,
            "significance": None,
            "consequences": None,
        },
        right_to_review="Under DSGVO Art. 22(3), you have the right to obtain "
        "human intervention, express your point of view, and contest "
        "any automated decision. Currently, no such decisions are made.",
    )


admin_router = APIRouter()


@admin_router.post("/employees/{employee_id}/restrict-processing", response_model=ProcessingRestrictionResponse)
def admin_restrict_employee_processing(
    employee_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: Restrict processing for a specific employee (DSGVO Art. 18)."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.processing_restricted = not employee.processing_restricted
    db.add(employee)
    db.flush()

    if employee.user_id:
        user = db.query(User).filter(User.id == employee.user_id).first()
        if user:
            user.processing_restricted = employee.processing_restricted
            db.add(user)
            db.flush()

    db.commit()
    db.refresh(employee)

    action = "restricted" if employee.processing_restricted else "unrestricted"
    audit_service.log(
        db,
        user_id=admin.id,
        action="GDPR_RESTRICT_PROCESSING",
        resource_type="employee",
        resource_id=str(employee_id),
        details=f"DSGVO Art. 18 admin: processing {action} for employee {employee_id}",
    )

    return ProcessingRestrictionResponse(
        message=f"Processing for employee {employee_id} has been {action}.",
        restricted=employee.processing_restricted,
    )


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
            headers={"Content-Disposition": f'attachment; filename="gdpr_export_employee_{employee_id}.csv"'},
        )

    data = export_user_data(db, user_id)
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": f'attachment; filename="gdpr_export_employee_{employee_id}.json"'},
    )
