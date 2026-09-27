from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.dependencies import get_current_user, get_db
from app.schemas.kiosk import KioskBoardResponse
from app.services.kiosk_service import get_kiosk_board

router = APIRouter()


@router.get("/board", response_model=KioskBoardResponse)
def get_kiosk_board_endpoint(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    team_id: int | None = Query(default=None),
):
    """Read-only shift board for kiosk displays (14-day window, completed schedules)."""
    response.headers["Cache-Control"] = "no-store"
    return get_kiosk_board(db, current_user, team_id=team_id)
