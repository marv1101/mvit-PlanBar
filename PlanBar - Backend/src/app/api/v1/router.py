from fastapi import APIRouter

from app.api.v1.audit import router as audit_router
from app.api.v1.callbacks import router as callbacks_router
from app.api.v1.exports import router as exports_router
from app.api.v1.gdpr import admin_router as gdpr_admin_router
from app.api.v1.gdpr import router as gdpr_router
from app.api.v1.retention import router as retention_router
from app.api.v1.shift_swaps import router as shift_swaps_router
from app.api.v1.self_service import router as self_service_router
from app.api.v1.employees import (
    contract_router,
    timecard_router,
)
from app.api.v1.employees import (
    router as employees_router,
)
from app.api.v1.health import router as health_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.pinboard import router as pinboard_router
from app.api.v1.privacy import router as privacy_router
from app.api.v1.push import router as push_router
from app.api.v1.requests import router as requests_router
from app.api.v1.roles import router as roles_router
from app.api.v1.schedules import router as schedules_router
from app.api.v1.sync import router as sync_router
from app.api.v1.teams import router as teams_router
from app.api.v1.time_tracking import router as time_tracking_router
from app.api.v1.users import router as users_router

api_router = APIRouter()
api_router.include_router(sync_router, prefix="", tags=["sync"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(employees_router, prefix="/employees", tags=["employees"])
api_router.include_router(contract_router, prefix="/contracts", tags=["contracts"])
api_router.include_router(timecard_router, prefix="/timecards", tags=["timecards"])
api_router.include_router(roles_router, prefix="/roles", tags=["roles"])
api_router.include_router(requests_router, prefix="/requests", tags=["requests"])
api_router.include_router(schedules_router, prefix="/schedules", tags=["schedules"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
api_router.include_router(push_router, prefix="/push", tags=["push"])
api_router.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
api_router.include_router(callbacks_router, prefix="/callbacks", tags=["callbacks"])
api_router.include_router(pinboard_router, prefix="/pinboard", tags=["pinboard"])
api_router.include_router(privacy_router, prefix="", tags=["privacy"])
api_router.include_router(audit_router, prefix="", tags=["audit"])
api_router.include_router(exports_router, prefix="/exports", tags=["exports"])
api_router.include_router(gdpr_router, prefix="/gdpr", tags=["gdpr"])
api_router.include_router(gdpr_admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(shift_swaps_router, prefix="/shift-swaps", tags=["shift-swaps"])
api_router.include_router(self_service_router, prefix="/my", tags=["self-service"])
api_router.include_router(teams_router, prefix="/teams", tags=["teams"])
api_router.include_router(time_tracking_router, prefix="/time-tracking", tags=["time-tracking"])
api_router.include_router(retention_router, prefix="/retention", tags=["retention"])
