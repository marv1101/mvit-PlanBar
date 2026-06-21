"""Integration tests for export API endpoints."""


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


def test_export_ical_requires_auth(client):
    response = client.get("/api/v1/exports/schedule/1/ical")
    assert response.status_code in (401, 403)


def test_export_pdf_requires_auth(client):
    response = client.get("/api/v1/exports/schedule/1/pdf")
    assert response.status_code in (401, 403)
