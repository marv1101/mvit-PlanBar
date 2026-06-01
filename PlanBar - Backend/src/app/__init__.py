from fastapi import FastAPI

from app.api.v1.router import api_router
from app.config import settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging(settings.log_format)
    app = FastAPI(
        title="PlanBar Backend",
        description="Backend API für PlanBar mit TiTO-Integration",
        version="0.1.0",
    )
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
