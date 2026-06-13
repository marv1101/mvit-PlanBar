from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_admin
from app.db.models.user import User
from app.services.metrics_service import get_aggregated_metrics, get_robustness_metrics

router = APIRouter()


@router.get("/")
def get_metrics(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return get_aggregated_metrics(db)


@router.get("/robustness")
def get_robustness(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return get_robustness_metrics(db)
