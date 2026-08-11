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


@pytest.fixture
def planer_auth_headers(client, db_session, auth_headers, planner_team):
    """Auth headers for a 'planer' role user linked to an employee in planner_team."""
    from app.db.models.user import User

    register_data = {
        "username": "testplaner",
        "email": "planer@test.com",
        "password": "TestPass@123",
    }
    client.post("/api/v1/users", json=register_data)

    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Plan", "last_name": "Er"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    user = db_session.query(User).filter(User.email == "planer@test.com").first()
    user.role = "planer"
    user.employee_id = emp_id
    db_session.add(user)
    db_session.commit()

    # Link employee to planner_team
    from app.db.models.employee import Employee
    from app.db.models.team import Team

    emp = db_session.query(Employee).filter(Employee.id == emp_id).first()
    team = db_session.query(Team).filter(Team.id == planner_team).first()
    emp.teams.append(team)
    db_session.commit()

    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "planer@test.com", "password": "TestPass@123"},
    )
    token = login_response.json()["access_token"]
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def planer_employee_id(db_session):
    """Return the employee_id of the planer user."""
    from app.db.models.user import User

    user = db_session.query(User).filter(User.email == "planer@test.com").first()
    return user.employee_id if user else None


@pytest.fixture
def planer_auth_headers_legacy_link(client, db_session, auth_headers, planner_team):
    """Auth headers for a 'planer' user linked to an employee ONLY via the
    reverse FK (employee.user_id set, user.employee_id left NULL).

    Mirrors legacy/one-sided data (e.g. dev DB 'testuser') that previously
    broke planer team-scope because team resolution only read user.employee_id.
    """
    from app.db.models.employee import Employee
    from app.db.models.team import Team
    from app.db.models.user import User

    register_data = {
        "username": "testplanerlegacy",
        "email": "planerlegacy@test.com",
        "password": "TestPass@123",
    }
    client.post("/api/v1/users", json=register_data)

    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Legacy", "last_name": "Planer"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    user = db_session.query(User).filter(User.email == "planerlegacy@test.com").first()
    user.role = "planer"
    assert user.employee_id is None
    db_session.add(user)
    db_session.commit()

    # Only the reverse link is set: employee.user_id -> user, user.employee_id stays NULL.
    emp = db_session.query(Employee).filter(Employee.id == emp_id).first()
    emp.user_id = user.id
    team = db_session.query(Team).filter(Team.id == planner_team).first()
    emp.teams.append(team)
    db_session.add(emp)
    db_session.commit()

    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "planerlegacy@test.com", "password": "TestPass@123"},
    )
    token = login_response.json()["access_token"]
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def planer_legacy_employee_id(db_session):
    """Return the employee_id of the legacy-link planer user."""
    from app.db.models.employee import Employee
    from app.db.models.user import User

    user = db_session.query(User).filter(User.email == "planerlegacy@test.com").first()
    if not user:
        return None
    emp = db_session.query(Employee).filter(Employee.user_id == user.id).first()
    return emp.id if emp else None


@pytest.fixture
def planner_team(client, auth_headers, db_session):
    """Create (or reuse) a team that the planer user is assigned to. Returns the team id."""
    name = "PlanerTeam"
    # Try to find existing team first to be idempotent across multiple test invocations
    listing = client.get("/api/v1/teams", headers=auth_headers).json()
    existing = next((t["id"] for t in listing["items"] if t["name"] == name), None)
    if existing is not None:
        return existing
    response = client.post(
        "/api/v1/teams",
        json={"name": name},
        headers=auth_headers,
    )
    if response.status_code == 201:
        return response.json()["id"]
    # Fall back to list lookup in case of conflict
    listing = client.get("/api/v1/teams", headers=auth_headers).json()
    return next(t["id"] for t in listing["items"] if t["name"] == name)
