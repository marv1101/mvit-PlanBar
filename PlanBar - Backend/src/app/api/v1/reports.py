from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_admin
from app.db.models.user import User
from app.schemas.report import ComplianceReportResponse, OvertimeReportResponse
from app.services.report_service import (
    export_compliance_pdf,
    export_overtime_pdf,
    generate_compliance_report,
    generate_overtime_report,
)

router = APIRouter()


@router.get("/overtime", response_model=OvertimeReportResponse)
def get_overtime_report(
    employee_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return generate_overtime_report(
        db,
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/compliance", response_model=ComplianceReportResponse)
def get_compliance_report(
    employee_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return generate_compliance_report(
        db,
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/overtime/pdf")
def export_overtime_report_pdf(
    employee_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    report_data = generate_overtime_report(
        db,
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
    )
    pdf_bytes = export_overtime_pdf(report_data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="ueberstunden-report.pdf"'},
    )


@router.get("/compliance/pdf")
def export_compliance_report_pdf(
    employee_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    report_data = generate_compliance_report(
        db,
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
    )
    pdf_bytes = export_compliance_pdf(report_data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="compliance-report.pdf"'},
    )
