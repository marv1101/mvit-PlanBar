"""Tests for export_service: iCal and PDF generation."""

import io
from datetime import UTC, date, datetime, time

import pytest
from app.db.base import Base
from app.db.models.employee import Employee
from app.db.models.schedule import Schedule, Shiftplan
from app.services.export_service import export_schedule_ical, export_schedule_pdf
from pypdf import PdfReader
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


def _create_rich_schedule(db):
    """Helper: create a two-week schedule with two colored employees (weeks A and B)."""
    schedule = Schedule(
        name="Reicher Plan",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 14),
        status="draft",
    )
    db.add(schedule)
    db.commit()

    max_emp = Employee(first_name="Max", last_name="Müller", color="#3b82f6")
    anna_emp = Employee(first_name="Anna", last_name="Schmidt", color="#ef4444")
    db.add_all([max_emp, anna_emp])
    db.commit()

    shifts = [
        Shiftplan(
            schedule_id=schedule.id,
            employee_id=max_emp.id,
            date=date(2026, 6, 1),
            shift_id="frueh",
            start_time=time(6, 0),
            end_time=time(14, 0),
            break_start="12:00",
            break_end="12:30",
            label="Fruehschicht",
            notes="Wichtig",
        ),
        Shiftplan(
            schedule_id=schedule.id,
            employee_id=max_emp.id,
            date=date(2026, 6, 2),
            shift_id="spaet",
            start_time=time(14, 0),
            end_time=time(22, 0),
            label="Spaetschicht",
        ),
        Shiftplan(
            schedule_id=schedule.id,
            employee_id=anna_emp.id,
            date=date(2026, 6, 8),
            shift_id="frueh",
            start_time=time(6, 0),
            end_time=time(14, 0),
            label="Fruehschicht",
        ),
        Shiftplan(
            schedule_id=schedule.id,
            employee_id=anna_emp.id,
            date=date(2026, 6, 9),
            shift_id="mittag",
            start_time=time(9, 0),
            end_time=time(17, 0),
            label="Mittagsschicht",
        ),
    ]
    db.add_all(shifts)
    db.commit()
    db.refresh(schedule)
    return schedule


def _pdf_pages(pdf_bytes: bytes):
    """Parse PDF bytes and return a list of pypdf Page objects."""
    return PdfReader(io.BytesIO(pdf_bytes)).pages


def _pdf_page_texts(pdf_bytes: bytes) -> list[str]:
    """Parse PDF bytes and return extracted text per page."""
    return [page.extract_text() or "" for page in _pdf_pages(pdf_bytes)]


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
    assert b"/Type /Page" in result
    # Empty schedule: cover page only
    assert len(PdfReader(io.BytesIO(result)).pages) == 1


# --- PDF layout & content tests (new spec) ---


def test_export_pdf_landscape_a4_mediabox(db_session):
    schedule = _create_rich_schedule(db_session)
    result = export_schedule_pdf(db_session, schedule.id)
    assert result is not None
    pages = _pdf_pages(result)
    assert pages  # at least one page
    for page in pages:
        assert float(page.mediabox.width) == pytest.approx(841.89, abs=0.5)
        assert float(page.mediabox.height) == pytest.approx(595.28, abs=0.5)


def test_export_pdf_page_structure(db_session):
    schedule = _create_rich_schedule(db_session)
    result = export_schedule_pdf(db_session, schedule.id)
    assert result is not None
    texts = _pdf_page_texts(result)
    assert len(texts) >= 3
    # Cover page (page 1)
    assert "Zusammenfassung" in texts[0]
    assert "Legende" in texts[0]
    # First calendar page (page 2) is week A
    assert "Kalender Woche A" in texts[1]
    # Schichtliste page exists and comes after all calendar pages
    kalender_idx = [i for i, t in enumerate(texts) if "Kalender" in t]
    list_idx = [i for i, t in enumerate(texts) if "Schichtliste" in t]
    assert list_idx
    assert max(kalender_idx) < min(list_idx)


def test_export_pdf_calendar_page_content(db_session):
    schedule = _create_rich_schedule(db_session)
    result = export_schedule_pdf(db_session, schedule.id)
    assert result is not None
    texts = _pdf_page_texts(result)
    week_a_pages = [t for t in texts if "Kalender Woche A" in t]
    assert week_a_pages
    page_text = week_a_pages[0]
    for needle in (
        "Montag",
        "01.06.",
        "Max",
        "06:00",
        "14:00",
        "Pause 12:00",
        "Fruehschicht",
    ):
        assert needle in page_text, f"missing {needle!r} on calendar week A page"
    # Empty days exist in week A (e.g. weekend) -> "Keine Schichten" somewhere
    assert any("Keine Schichten" in t for t in texts)


def test_export_pdf_list_page_content(db_session):
    schedule = _create_rich_schedule(db_session)
    result = export_schedule_pdf(db_session, schedule.id)
    assert result is not None
    texts = _pdf_page_texts(result)
    list_pages = [t for t in texts if "Schichtliste" in t]
    assert list_pages
    page_text = list_pages[0]
    for needle in (
        "Montag, 01.06.2026",
        "Max Müller",
        "Anna Schmidt",
        "22:00",
        "Wichtig",
    ):
        assert needle in page_text, f"missing {needle!r} on Schichtliste page"
    # Chronological ordering in extracted text
    assert page_text.index("01.06.2026") < page_text.index("08.06.2026")


def test_export_pdf_week_b_separate_calendar_page(db_session):
    schedule = _create_rich_schedule(db_session)
    result = export_schedule_pdf(db_session, schedule.id)
    assert result is not None
    texts = _pdf_page_texts(result)
    a_pages = [t for t in texts if "Kalender Woche A" in t]
    b_pages = [t for t in texts if "Kalender Woche B" in t]
    assert a_pages and b_pages
    # Week B page only contains Anna, week A page only contains Max
    assert "Anna" in b_pages[0]
    assert "Max" not in b_pages[0]
    assert "Max" in a_pages[0]
    assert "Anna" not in a_pages[0]


def test_export_pdf_employee_colors(db_session):
    schedule = _create_rich_schedule(db_session)
    result = export_schedule_pdf(db_session, schedule.id)
    assert result is not None
    pages = _pdf_pages(result)
    texts = [page.extract_text() or "" for page in pages]
    a_page = pages[next(i for i, t in enumerate(texts) if "Kalender Woche A" in t)]
    b_page = pages[next(i for i, t in enumerate(texts) if "Kalender Woche B" in t)]
    blue = f"{59 / 255:.4f} {130 / 255:.4f} {246 / 255:.4f}".encode()
    red = f"{239 / 255:.4f} {68 / 255:.4f} {68 / 255:.4f}".encode()
    assert blue in a_page.get_contents().get_data()
    assert red in b_page.get_contents().get_data()


def test_export_pdf_umlauts_preserved(db_session):
    schedule = _create_rich_schedule(db_session)
    result = export_schedule_pdf(db_session, schedule.id)
    assert result is not None
    texts = _pdf_page_texts(result)
    assert any("Müller" in t for t in texts)
    assert not any("Mueller" in t for t in texts)


def test_export_pdf_footer_berlin_timezone(db_session, monkeypatch):
    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is not None and str(tz) == "Europe/Berlin":
                return datetime(2026, 6, 1, 14, 30, tzinfo=tz)
            return datetime(2026, 6, 1, 12, 30, tzinfo=UTC)

    monkeypatch.setattr("app.services.export_service.datetime", FakeDateTime)
    schedule = _create_rich_schedule(db_session)
    result = export_schedule_pdf(db_session, schedule.id)
    assert result is not None
    texts = _pdf_page_texts(result)
    assert any("Exportiert am 01.06.2026 14:30" in t for t in texts)
