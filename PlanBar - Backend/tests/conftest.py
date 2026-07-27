import os

import httpx

# Must be set before any app imports so the engine uses SQLite
TEST_DATABASE_URL = "sqlite:///./test_planbar.db"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["ENVIRONMENT"] = "test"
# Tests rely on the public self-registration endpoint (test_users.py etc.).
# Issue #163 flips the default to False in production; tests opt in here.
os.environ["ENABLE_SELF_REGISTRATION"] = "true"

import pytest
from app.config import settings
from app.core.rate_limit import limiter
from app.db.base import Base
from app.dependencies import get_db
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

settings.database_url = TEST_DATABASE_URL
settings.tito_api_key = None

_test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(bind=_test_engine, autoflush=False, autocommit=False)


class CsrfTestClient(TestClient):
    """TestClient that automatically handles double-submit cookie CSRF protection.

    On first use, a GET is issued to obtain the ``csrf_token`` cookie.
    Every subsequent mutating request (POST / PUT / PATCH / DELETE) automatically
    includes the ``X-CSRF-Token`` header so that existing tests don't need
    to be aware of CSRF at all.
    """

    _CSRF_COOKIE = "csrf_token"
    _CSRF_HEADER = "X-CSRF-Token"
    _MUTATING = frozenset({"POST", "PUT", "PATCH", "DELETE"})

    def request(self, method: str, url: httpx.URL | str, **kwargs):
        # Ensure we have a CSRF token cookie
        if self._CSRF_COOKIE not in self.cookies:
            super().request("GET", "/api/v1/health/ping")

        # Inject the header for mutating requests when not already present
        if method.upper() in self._MUTATING and self._CSRF_HEADER not in (kwargs.get("headers") or {}):
            headers = dict(kwargs.get("headers") or {})
            headers[self._CSRF_HEADER] = self.cookies.get(self._CSRF_COOKIE, "")
            kwargs["headers"] = headers

        return super().request(method, url, **kwargs)


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
def raw_client(db_session):
    """Plain TestClient without CSRF auto-injection (for testing CSRF itself)."""
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
def client(db_session):
    limiter.enabled = False
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return CsrfTestClient(app)


@pytest.fixture
def auth_headers(client, db_session):
    from app.db.models.user import User

    register_data = {
        "username": "testadmin",
        "email": "admin@test.com",
        "password": "TestPass@123",
    }
    client.post("/api/v1/users", json=register_data)
    user = db_session.query(User).filter(User.email == "admin@test.com").first()
    if user:
        user.role = "admin"
        db_session.add(user)
        db_session.commit()
    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "admin@test.com", "password": "TestPass@123"},
    )
    token = login_response.json()["access_token"]
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def employee_auth_headers(client, db_session, auth_headers):
    from app.db.models.user import User

    register_data = {
        "username": "testemployee",
        "email": "employee@test.com",
        "password": "TestPass@123",
    }
    client.post("/api/v1/users", json=register_data)

    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Test", "last_name": "Employee"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    user = db_session.query(User).filter(User.email == "employee@test.com").first()
    user.employee_id = emp_id
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "employee@test.com", "password": "TestPass@123"},
    )
    token = login_response.json()["access_token"]
    client.cookies.clear()
    return ({"Authorization": f"Bearer {token}"}, emp_id)
