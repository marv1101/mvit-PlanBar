"""Export endpoints for schedule PDF and iCal files."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.db.models.user import User
from app.services.export_service import export_schedule_ical, export_schedule_pdf

router = APIRouter()


@router.get("/schedule/{schedule_id}/ical")
def download_schedule_ical(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the schedule as an iCal (.ics) file."""
    ical_bytes = export_schedule_ical(db, schedule_id)
    if ical_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )
    return Response(
        content=ical_bytes,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="schichtplan-{schedule_id}.ics"'},
    )


@router.get("/schedule/{schedule_id}/pdf")
def download_schedule_pdf(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the schedule as a PDF file."""
    pdf_bytes = export_schedule_pdf(db, schedule_id)
    if pdf_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="schichtplan-{schedule_id}.pdf"'},
    )
