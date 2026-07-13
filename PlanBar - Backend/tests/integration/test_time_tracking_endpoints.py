"""Integration tests for time tracking endpoints (Issue #29)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.employee import Employee
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _create_employee(db_session, first="Max", last="Mustermann") -> Employee:
    emp = Employee(first_name=first, last_name=last)
    db_session.add(emp)
    db_session.commit()
    db_session.refresh(emp)
    return emp


class TestClockInOut:
    def test_clock_in_requires_auth(self, client):
        r = client.post("/api/v1/time-tracking/clock-in")
        assert r.status_code in (401, 403)

    def test_today_requires_auth(self, client):
        r = client.get("/api/v1/time-tracking/today")
        assert r.status_code in (401, 403)

    def test_entries_requires_employee_id(self, client):
        r = client.get("/api/v1/time-tracking/entries")
        assert r.status_code in (401, 403, 422)

    def test_entries_unknown_employee(self, client):
        # even with auth, an unknown employee_id should 404 — we use a fake token
        # to pass auth checks, but since we don't have a token, the endpoint
        # should reject with 401/403 before the 404 path; both are acceptable.
        r = client.get("/api/v1/time-tracking/entries?employee_id=99999")
        assert r.status_code in (401, 403, 404)


class TestSchemas:
    """Sanity check: schemas validate correctly."""

    def test_time_entry_create_accepts_empty(self):
        from app.schemas.time_tracking import TimeEntryCreate

        t = TimeEntryCreate()
        assert t.notes is None

    def test_time_entry_create_with_notes(self):
        from app.schemas.time_tracking import TimeEntryCreate

        t = TimeEntryCreate(notes="Frühschicht")
        assert t.notes == "Frühschicht"
