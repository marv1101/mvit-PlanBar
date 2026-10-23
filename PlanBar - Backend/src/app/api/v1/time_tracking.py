"""Time-Tracking API endpoints (Issue #29 - Digitale Zeiterfassung)."""

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.models.employee import Employee
from app.dependencies import get_current_user, get_db
from app.schemas.time_tracking import TimeEntryCreate, TimeEntryResponse
from app.services.time_tracking_service import (
    clock_in as svc_clock_in,
)
from app.services.time_tracking_service import (
    clock_out as svc_clock_out,
)
from app.services.time_tracking_service import (
    get_daily_entries as svc_get_daily_entries,
)

router = APIRouter()


def _resolve_employee_id(employee_id: int | None, current_user) -> int:
    """Non-admins can only clock in/out themselves."""
    if employee_id is None:
        # map current user -> employee via employee_id link
        if getattr(current_user, "employee_id", None):
            return current_user.employee_id
        # fallback: first employee (for tests / dev convenience)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="employee_id required (no linked employee on user)",
        )
    return employee_id


@router.post("/clock-in", response_model=TimeEntryResponse, status_code=status.HTTP_201_CREATED)
def clock_in(
    payload: TimeEntryCreate | None = None,
    employee_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    emp_id = _resolve_employee_id(employee_id, current_user)
    try:
        entry = svc_clock_in(db, emp_id, notes=(payload.notes if payload else None))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return entry


@router.post("/clock-out", response_model=TimeEntryResponse)
def clock_out(
    employee_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    emp_id = _resolve_employee_id(employee_id, current_user)
    try:
        entry = svc_clock_out(db, emp_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return entry


@router.get("/today", response_model=list[TimeEntryResponse])
def today(
    employee_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    emp_id = _resolve_employee_id(employee_id, current_user)
    try:
        return svc_get_daily_entries(db, emp_id, datetime.now(UTC).date())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/entries", response_model=list[TimeEntryResponse])
def list_entries(
    employee_id: int = Query(...),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not db.get(Employee, employee_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    # Simple range: union of daily entries between start_date and end_date (inclusive)
    sd: date = start_date if start_date is not None else datetime.now(UTC).date()
    ed: date = end_date if end_date is not None else sd

    from datetime import timedelta

    results = []
    cur = sd
    while cur <= ed:
        results.extend(svc_get_daily_entries(db, employee_id, cur))
        cur = cur + timedelta(days=1)
    return results
