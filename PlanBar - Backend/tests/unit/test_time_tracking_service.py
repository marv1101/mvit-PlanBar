from datetime import datetime, timedelta, timezone

import pytest
from app.db.base import Base
from app.db.models.employee import Employee
from app.db.models.time_tracking import TimeEntry
from app.services.time_tracking_service import (
    clock_in,
    clock_out,
    get_daily_entries,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def employee(db_session):
    emp = Employee(first_name="Max", last_name="Mustermann")
    db_session.add(emp)
    db_session.commit()
    db_session.refresh(emp)
    return emp


class TestClockIn:
    def test_clock_in_creates_entry(self, db_session, employee):
        entry = clock_in(db_session, employee.id)
        assert entry.id is not None
        assert entry.employee_id == employee.id
        assert entry.clock_in is not None
        assert entry.clock_out is None
        assert entry.duration_minutes is None

    def test_clock_in_with_notes(self, db_session, employee):
        entry = clock_in(db_session, employee.id, notes="Fruehschicht")
        assert entry.notes == "Fruehschicht"

    def test_clock_in_prevents_duplicate_open_entry(self, db_session, employee):
        clock_in(db_session, employee.id)
        with pytest.raises(ValueError, match="already clocked in"):
            clock_in(db_session, employee.id)

    def test_clock_in_nonexistent_employee(self, db_session):
        with pytest.raises(ValueError, match="Employee not found"):
            clock_in(db_session, 99999)


class TestClockOut:
    def test_clock_out_closes_entry(self, db_session, employee):
        clock_in(db_session, employee.id)
        entry = clock_out(db_session, employee.id)
        assert entry.clock_out is not None
        assert entry.duration_minutes is not None
        assert entry.duration_minutes >= 0

    def test_clock_out_calculates_duration(self, db_session, employee):
        entry = clock_in(db_session, employee.id)
        entry.clock_in = datetime.now(timezone.utc) - timedelta(hours=2)
        db_session.commit()
        db_session.refresh(entry)

        entry = clock_out(db_session, employee.id)
        assert entry.duration_minutes == 120

    def test_clock_out_no_open_entry(self, db_session, employee):
        with pytest.raises(ValueError, match="No open time entry"):
            clock_out(db_session, employee.id)

    def test_clock_out_nonexistent_employee(self, db_session):
        with pytest.raises(ValueError, match="Employee not found"):
            clock_out(db_session, 99999)


class TestGetDailyEntries:
    def test_get_daily_entries_empty(self, db_session, employee):
        today = datetime.now(timezone.utc).date()
        entries = get_daily_entries(db_session, employee.id, today)
        assert entries == []

    def test_get_daily_entries_returns_today(self, db_session, employee):
        clock_in(db_session, employee.id)
        today = datetime.now(timezone.utc).date()
        entries = get_daily_entries(db_session, employee.id, today)
        assert len(entries) == 1

    def test_get_daily_entries_excludes_other_days(self, db_session, employee):
        entry = TimeEntry(
            employee_id=employee.id,
            clock_in=datetime.now(timezone.utc) - timedelta(days=2),
            clock_out=datetime.now(timezone.utc) - timedelta(days=2, hours=-8),
            duration_minutes=480,
        )
        db_session.add(entry)
        db_session.commit()

        today = datetime.now(timezone.utc).date()
        entries = get_daily_entries(db_session, employee.id, today)
        assert len(entries) == 0

    def test_get_daily_entries_multiple_same_day(self, db_session, employee):
        # Use a reference time well into the day so all 3 entries (offset by 4h)
        # fall on the same calendar date in UTC.
        ref = datetime(2026, 7, 13, 12, 0, 0, tzinfo=timezone.utc)
        for i in range(3):
            entry = TimeEntry(
                employee_id=employee.id,
                clock_in=ref + timedelta(hours=i * 4),
                clock_out=ref + timedelta(hours=i * 4 + 8),
                duration_minutes=480,
            )
            db_session.add(entry)
        db_session.commit()

        target = ref.date()
        entries = get_daily_entries(db_session, employee.id, target)
        assert len(entries) == 3
