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
from app.middleware.error_handler import http_error_handler, validation_exception_handler
from app.middleware.request_logging import RequestLoggingMiddleware
from app.schemas.user import UserCreate
from app.services.user_service import create_user
from sqlalchemy import inspect, text

from app.db.models.user import User


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="PlanBar Backend",
        description="Backend API für PlanBar mit TiTO-Integration",
        version="0.1.0"
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(api_router, prefix="/api/v1")
    create_database()
    run_migrations()
    seed_initial_users()
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    return app


def run_migrations() -> None:
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("users")]
    if "must_change_password" not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 1"))
            conn.commit()


def seed_initial_users() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "admin@mphion.de").first() is None:
            create_user(
                db,
                UserCreate(
                    username="admin",
                    email="admin@mphion.de",
                    password="Admin@123",
                ),
                role="admin",
            )
        if db.query(User).filter(User.email == "testuser@mphion.de").first() is None:
            create_user(
                db,
                UserCreate(
                    username="testuser",
                    email="testuser@mphion.de",
                    password="User@123",
                ),
            )
    finally:
        db.close()


def create_database() -> None:
    Base.metadata.create_all(bind=engine)


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
