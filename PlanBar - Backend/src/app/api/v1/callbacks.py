import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import NotFoundException, UnauthorizedException
from app.dependencies import get_db
from app.schemas.tito import TiTOCallbackPayload
from app.services.tito_callback import CallbackConflictError, process_tito_callback

logger = logging.getLogger(__name__)

router = APIRouter()


def verify_tito_callback_auth(request: Request) -> None:
    """Verify the callback's shared secret (contract v2).

    TiTO authenticates with `Authorization: Bearer {key}`; an `X-API-Key`
    header is accepted as an alternative. The api_key query parameter is
    NOT accepted anymore (it leaked into TiTO DBs/logs via the callback URL).
    """
    if settings.tito_api_key:
        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")
        bearer_valid = bool(
            auth_header
            and auth_header.startswith("Bearer ")
            and hmac.compare_digest(auth_header[7:], settings.tito_api_key)
        )
        header_valid = bool(api_key_header and hmac.compare_digest(api_key_header, settings.tito_api_key))
        if not bearer_valid and not header_valid:
            raise UnauthorizedException(detail="Invalid or missing API key")
    else:
        if settings.environment != "development":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="TiTO callback not available: API key not configured",
            )
        logger.warning("tito_api_key is not set — allowing TiTO callback without authentication")


@router.post(
    "/tito",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tito_callback_auth)],
)
def tito_callback(
    payload: TiTOCallbackPayload,
    db: Session = Depends(get_db),
):
    try:
        schedule = process_tito_callback(db, payload)
    except CallbackConflictError as exc:
        # A3: 409 so TiTO gives up after its retry limit instead of looping.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not schedule:
        raise NotFoundException(detail="No schedule found for this job")
    return {"status": "processed", "schedule_id": schedule.id}
