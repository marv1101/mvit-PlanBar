from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_admin
from app.db.models.user import User
from app.services.tito_proxy import tito_proxy

router = APIRouter()


@router.get("/ping")
def ping():
    return {"status": "ok"}


@router.get("/ready")
def ready():
    return {"status": "ready"}


@router.get("/db")
def db_health(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        return {"status": "error", "detail": "Database connection failed"}


@router.get("/tito")
async def tito_health(admin: User = Depends(require_admin)):
    healthy = await tito_proxy.check_health()
    return {"status": "ok" if healthy else "unreachable"}
