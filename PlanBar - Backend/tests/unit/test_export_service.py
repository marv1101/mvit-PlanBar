"""Tests for export_service: iCal and PDF generation."""

from datetime import date, time

import pytest
from app.db.base import Base
from app.db.models.employee import Employee
from app.db.models.schedule import Schedule, Shiftplan
from app.services.export_service import export_schedule_ical, export_schedule_pdf
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


def _create_schedule_with_shifts(db, name="Test Plan"):
    """Helper: create a schedule with two shifts and return (schedule, shifts)."""
    schedule = Schedule(
        name=name,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
    )
    db.add(schedule)
    db.commit()

    emp = Employee(first_name="Max", last_name="Mustermann")
    db.add(emp)
    db.commit()

    sp1 = Shiftplan(
        schedule_id=schedule.id,
        employee_id=emp.id,
        date=date(2026, 6, 1),
        shift_id="frueh",
        start_time=time(6, 0),
        end_time=time(14, 0),
        label="Fruehschicht",
        notes="Wichtig",
    )
    sp2 = Shiftplan(
        schedule_id=schedule.id,
        employee_id=emp.id,
        date=date(2026, 6, 2),
        shift_id="spaet",
        start_time=time(14, 0),
        end_time=time(22, 0),
        label="Spaetschicht",
    )
    db.add_all([sp1, sp2])
    db.commit()
    db.refresh(schedule)
    return schedule


# --- iCal tests ---


def test_export_ical_not_found(db_session):
    result = export_schedule_ical(db_session, 99999)
    assert result is None


def test_export_ical_returns_bytes(db_session):
    schedule = _create_schedule_with_shifts(db_session)
    result = export_schedule_ical(db_session, schedule.id)
    assert result is not None
    assert isinstance(result, bytes)


def test_export_ical_contains_events(db_session):
    schedule = _create_schedule_with_shifts(db_session)
    result = export_schedule_ical(db_session, schedule.id)
    assert result is not None
    ical_text = result.decode("utf-8")
    assert "BEGIN:VEVENT" in ical_text
    assert "Fruehschicht" in ical_text
    assert "Max Mustermann" in ical_text
    assert "Spaetschicht" in ical_text


def test_export_ical_calendar_name(db_session):
    schedule = _create_schedule_with_shifts(db_session, name="Mein Plan")
    result = export_schedule_ical(db_session, schedule.id)
    assert result is not None
    ical_text = result.decode("utf-8")
    assert "X-WR-CALNAME:Mein Plan" in ical_text


def test_export_ical_empty_schedule(db_session):
    schedule = Schedule(
        name="Leerer Plan",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
    )
    db_session.add(schedule)
    db_session.commit()
    result = export_schedule_ical(db_session, schedule.id)
    assert result is not None
    ical_text = result.decode("utf-8")
    assert "BEGIN:VCALENDAR" in ical_text
    # No events in empty schedule
    assert "BEGIN:VEVENT" not in ical_text


# --- PDF tests ---


def test_export_pdf_not_found(db_session):
    result = export_schedule_pdf(db_session, 99999)
    assert result is None


def test_export_pdf_returns_bytes(db_session):
    schedule = _create_schedule_with_shifts(db_session)
    result = export_schedule_pdf(db_session, schedule.id)
    assert result is not None
    assert isinstance(result, bytes)


def test_export_pdf_starts_with_magic(db_session):
    schedule = _create_schedule_with_shifts(db_session)
    result = export_schedule_pdf(db_session, schedule.id)
    assert result is not None
    # PDF magic bytes
    assert result[:5] == b"%PDF-"


def test_export_pdf_contains_pdf_structure(db_session):
    schedule = _create_schedule_with_shifts(db_session, name="PDF Test Plan")
    result = export_schedule_pdf(db_session, schedule.id)
    assert result is not None
    # Verify PDF structure (content is compressed, so check structural markers)
    assert result[:5] == b"%PDF-"
    assert b"/Type /Catalog" in result  # PDF catalog object
    assert b"/Type /Page" in result  # Page objects exist
    assert b"/BaseFont /Helvetica" in result  # Font is embedded


def test_export_pdf_empty_schedule(db_session):
    schedule = Schedule(
        name="Leerer PDF Plan",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="draft",
    )
    db_session.add(schedule)
    db_session.commit()
    result = export_schedule_pdf(db_session, schedule.id)
    assert result is not None
    assert result[:5] == b"%PDF-"
    # Should have at least one page (title page only, no shift table)
    assert b"/Type /Page" in result
