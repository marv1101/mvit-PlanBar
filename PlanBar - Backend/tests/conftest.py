import os

# Must be set before any app imports so the engine uses SQLite
TEST_DATABASE_URL = "sqlite:///./test_planbar.db"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["ENVIRONMENT"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.core.rate_limit import limiter
from app.db.base import Base
from app.dependencies import get_db
from app.main import create_app

settings.database_url = TEST_DATABASE_URL

_test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(bind=_test_engine, autoflush=False, autocommit=False)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture
def db_session():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client(db_session):
    limiter.enabled = False
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def auth_headers(client, db_session):
    from app.db.models.user import User

    register_data = {
        "username": "testadmin",
        "email": "admin@test.com",
        "password": "testpassword123",
    }
    client.post("/api/v1/users", json=register_data)
    user = db_session.query(User).filter(User.email == "admin@test.com").first()
    if user:
        user.role = "admin"
        db_session.add(user)
        db_session.commit()
    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "admin@test.com", "password": "testpassword123"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
