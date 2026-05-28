from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.dependencies import get_db
from app.schemas.tito import TiTOCallbackPayload
from app.services.tito_callback import process_tito_callback

router = APIRouter()


@router.post("/tito", status_code=status.HTTP_200_OK)
def tito_callback(
    payload: TiTOCallbackPayload,
    db: Session = Depends(get_db),
):
    schedule = process_tito_callback(db, payload)
    if not schedule:
        raise NotFoundException(detail="No schedule found for this job")
    return {"status": "processed", "schedule_id": schedule.id}
