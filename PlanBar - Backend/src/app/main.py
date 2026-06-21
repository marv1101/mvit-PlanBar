from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.rate_limit import limiter

from app.api.v1.router import api_router
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.database import SessionLocal, engine
from app.config import settings
from app.middleware.error_handler import (
    http_error_handler,
    validation_exception_handler,
)
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.request_size_limit import RequestSizeLimitMiddleware
from app.middleware.security_headers import (
    HttpsRedirectMiddleware,
    SecurityHeadersMiddleware,
)
from app.schemas.user import UserCreate
from app.services.user_service import create_user
from alembic.config import Config
from alembic import command

from app.db.models.user import User
import logging
import uuid

logger = logging.getLogger(__name__)


def _verify_production_settings():
    if settings.environment in ("production", "demo", "staging"):
        if settings.secret_key in ("change-me-in-production", "", None):
            raise RuntimeError(
                "SECRET_KEY must be set to a secure value in production. Generate one with: openssl rand -hex 32"
            )
        if "sqlite" in settings.database_url:
            raise RuntimeError(
                "SQLite is not supported in production. Set DATABASE_URL to a PostgreSQL connection string."
            )


def create_app() -> FastAPI:
    configure_logging()
    _verify_production_settings()
    app = FastAPI(
        title="PlanBar Backend",
        description="Backend API für PlanBar mit TiTO-Integration",
        version="0.1.0",
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(HttpsRedirectMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(",") if settings.cors_origins else ["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "X-Requested-With",
            "X-CSRF-Token",
        ],
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024)
    app.include_router(api_router, prefix="/api/v1")
    run_database_setup()
    seed_initial_users()
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    return app


def run_database_setup() -> None:
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully")
    except Exception:
        logger.warning("Alembic migration failed, falling back to create_all")
        Base.metadata.create_all(bind=engine)


def seed_initial_users() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "admin@mphion.de").first() is None:
            admin_password = uuid.uuid4().hex[:12]
            create_user(
                db,
                UserCreate(
                    username="admin",
                    email="admin@mphion.de",
                    password=admin_password,
                ),
                role="admin",
            )
            logger.info("=" * 60)
            logger.info("Initial-Passwort fuer admin@mphion.de: %s", admin_password)
            logger.info("=" * 60)

        if db.query(User).filter(User.email == "testuser@mphion.de").first() is None:
            test_password = uuid.uuid4().hex[:12]
            create_user(
                db,
                UserCreate(
                    username="testuser",
                    email="testuser@mphion.de",
                    password=test_password,
                ),
            )
            logger.info("=" * 60)
            logger.info("Initial-Passwort fuer testuser@mphion.de: %s", test_password)
            logger.info("=" * 60)
    finally:
        db.close()


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
