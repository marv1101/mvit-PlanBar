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
from app.middleware.csrf import CsrfMiddleware
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

from pathlib import Path

logger = logging.getLogger(__name__)


def _write_credentials_to_file(email: str, password: str) -> None:
    """Write initial credentials to a one-time file (production only).

    The file is meant to be read once during initial setup and then deleted.
    Passwords are never written to logs or stdout in production.
    """
    creds_path = Path("initial-credentials.txt")
    with open(creds_path, "a") as f:
        f.write(f"{email}: {password}\n")


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
    app.add_middleware(CsrfMiddleware)
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


def _generate_complex_password() -> str:
    """Generate a password that meets complexity requirements.

    Returns a 16-character password with:
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character
    """
    import random
    import string

    # Ensure at least one of each required character type
    uppercase = random.choice(string.ascii_uppercase)
    lowercase = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    special = random.choice('!@#$%^&*')
    # Fill the rest with random characters from all categories
    rest = ''.join(random.choices(string.ascii_letters + string.digits + '!@#$%^&*', k=12))
    # Combine and shuffle
    password = list(uppercase + lowercase + digit + special + rest)
    random.shuffle(password)
    return ''.join(password)


def seed_initial_users() -> None:
    env = settings.environment
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "admin@mphion.de").first() is None:
            admin_password = _generate_complex_password()
            create_user(
                db,
                UserCreate(
                    username="admin",
                    email="admin@mphion.de",
                    password=admin_password,
                ),
                role="admin",
            )
            if env == "development":
                print(f"\n{'=' * 60}")
                print(f"Initial-Passwort fuer admin@mphion.de: {admin_password}")
                print(f"{'=' * 60}\n")
            elif env in ("production", "demo", "staging"):
                _write_credentials_to_file("admin@mphion.de", admin_password)
                logger.warning(
                    "Initial credentials for admin@mphion.de written to initial-credentials.txt"
                )

        if db.query(User).filter(User.email == "testuser@mphion.de").first() is None:
            test_password = _generate_complex_password()
            create_user(
                db,
                UserCreate(
                    username="testuser",
                    email="testuser@mphion.de",
                    password=test_password,
                ),
            )
            if env == "development":
                print(f"\n{'=' * 60}")
                print(f"Initial-Passwort fuer testuser@mphion.de: {test_password}")
                print(f"{'=' * 60}\n")
            elif env in ("production", "demo", "staging"):
                _write_credentials_to_file("testuser@mphion.de", test_password)
                logger.warning(
                    "Initial credentials for testuser@mphion.de written to initial-credentials.txt"
                )
    finally:
        db.close()


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
