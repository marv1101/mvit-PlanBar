"""Integration tests for export API endpoints."""

import io
from datetime import date, time

import pytest
from app.db.models.employee import Employee
from app.db.models.schedule import Shiftplan
from pypdf import PdfReader


def test_export_ical_endpoint(client, auth_headers):
    # Create schedule
    create_resp = client.post(
        "/api/v1/schedules",
        json={"name": "iCal Export Test", "start_date": "2026-06-01", "end_date": "2026-06-07"},
        headers=auth_headers,
    )
    schedule_id = create_resp.json()["id"]

    response = client.get(f"/api/v1/exports/schedule/{schedule_id}/ical", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/calendar; charset=utf-8"
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "BEGIN:VCALENDAR" in response.text


def test_export_ical_not_found(client, auth_headers):
    response = client.get("/api/v1/exports/schedule/99999/ical", headers=auth_headers)
    assert response.status_code == 404


def test_export_pdf_endpoint(client, auth_headers):
    # Create schedule
    create_resp = client.post(
        "/api/v1/schedules",
        json={"name": "PDF Export Test", "start_date": "2026-06-01", "end_date": "2026-06-07"},
        headers=auth_headers,
    )
    schedule_id = create_resp.json()["id"]

    response = client.get(f"/api/v1/exports/schedule/{schedule_id}/pdf", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers.get("content-disposition", "")
    assert response.content[:5] == b"%PDF-"


def test_export_pdf_not_found(client, auth_headers):
    response = client.get("/api/v1/exports/schedule/99999/pdf", headers=auth_headers)
    assert response.status_code == 404


def test_export_pdf_landscape_a4_via_endpoint(client, auth_headers, db_session):
    # Create a schedule with a date range and one shift so the PDF has
    # multiple pages (cover, calendar, list).
    create_resp = client.post(
        "/api/v1/schedules",
        json={
            "name": "Landscape A4 Test",
            "start_date": "2026-06-01",
            "end_date": "2026-06-07",
        },
        headers=auth_headers,
    )
    schedule_id = create_resp.json()["id"]

    emp = Employee(first_name="Max", last_name="Müller", color="#3b82f6")
    db_session.add(emp)
    db_session.commit()
    db_session.add(
        Shiftplan(
            schedule_id=schedule_id,
            employee_id=emp.id,
            date=date(2026, 6, 1),
            shift_id="frueh",
            start_time=time(6, 0),
            end_time=time(14, 0),
            label="Fruehschicht",
        )
    )
    db_session.commit()

    response = client.get(f"/api/v1/exports/schedule/{schedule_id}/pdf", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:5] == b"%PDF-"

    reader = PdfReader(io.BytesIO(response.content))
    assert len(reader.pages) >= 1
    for page in reader.pages:
        assert float(page.mediabox.width) == pytest.approx(841.89, abs=0.5)
        assert float(page.mediabox.height) == pytest.approx(595.28, abs=0.5)


def test_export_ical_requires_auth(client):
    response = client.get("/api/v1/exports/schedule/1/ical")
    assert response.status_code in (401, 403)


def test_export_pdf_requires_auth(client):
    response = client.get("/api/v1/exports/schedule/1/pdf")
    assert response.status_code in (401, 403)
