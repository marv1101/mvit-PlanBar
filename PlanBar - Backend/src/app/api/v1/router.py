from fastapi import APIRouter

from app.api.v1.callbacks import router as callbacks_router
from app.api.v1.employees import (
    contract_router,
    router as employees_router,
    timecard_router,
)
from app.api.v1.health import router as health_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.pinboard import router as pinboard_router
from app.api.v1.requests import router as requests_router
from app.api.v1.roles import router as roles_router
from app.api.v1.schedules import router as schedules_router
from app.api.v1.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(employees_router, prefix="/employees", tags=["employees"])
api_router.include_router(contract_router, prefix="/contracts", tags=["contracts"])
api_router.include_router(timecard_router, prefix="/timecards", tags=["timecards"])
api_router.include_router(roles_router, prefix="/roles", tags=["roles"])
api_router.include_router(requests_router, prefix="/requests", tags=["requests"])
api_router.include_router(schedules_router, prefix="/schedules", tags=["schedules"])
api_router.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
api_router.include_router(callbacks_router, prefix="/callbacks", tags=["callbacks"])
api_router.include_router(pinboard_router, prefix="/pinboard", tags=["pinboard"])
