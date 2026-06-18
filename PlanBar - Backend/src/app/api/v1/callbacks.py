import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import NotFoundException, UnauthorizedException
from app.dependencies import get_db
from app.schemas.tito import TiTOCallbackPayload
from app.services.tito_callback import process_tito_callback

logger = logging.getLogger(__name__)

router = APIRouter()


def verify_tito_callback_auth(request: Request) -> None:
    if settings.tito_api_key:
        auth_header = request.headers.get("Authorization")
        if (
            not auth_header
            or not auth_header.startswith("Bearer ")
            or not hmac.compare_digest(auth_header[7:], settings.tito_api_key)
        ):
            raise UnauthorizedException(detail="Invalid or missing API key")
    else:
        if settings.environment != "development":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="TiTO callback not available: API key not configured",
            )
        logger.warning("tito_api_key is not set — allowing TiTO callback without authentication")


@router.post("/tito", status_code=status.HTTP_200_OK, dependencies=[Depends(verify_tito_callback_auth)])
def tito_callback(
    payload: TiTOCallbackPayload,
    db: Session = Depends(get_db),
):
    schedule = process_tito_callback(db, payload)
    if not schedule:
        raise NotFoundException(detail="No schedule found for this job")
    return {"status": "processed", "schedule_id": schedule.id}
