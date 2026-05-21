from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
def ping():
    return {"status": "ok"}

@router.get("/ready")
def ready():
    return {"status": "ready"}
