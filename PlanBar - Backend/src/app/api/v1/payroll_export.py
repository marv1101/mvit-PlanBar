"""Payroll export API endpoints (Issue #31 - Lohnabrechnungs-Export Phase 1)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.dependencies import get_current_user, get_db
from app.services.payroll_export_service import (
    generate_payroll_csv as svc_generate_payroll_csv,
)

router = APIRouter()


@router.get("/csv")
def payroll_csv(
    employee_id: int = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.db.models.employee import Employee

    if not db.get(Employee, employee_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    if current_user.role != "admin" and current_user.employee_id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to export payroll for other employees",
        )

    try:
        csv_bytes = svc_generate_payroll_csv(db, employee_id, start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="lohnabrechnung-{employee_id}.csv"'},
    )
