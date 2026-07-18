"""Integration tests for payroll export endpoints (Issue #31)."""
from datetime import datetime, timedelta, timezone

from app.db.models.employee import Employee
from app.db.models.time_tracking import TimeEntry
from app.db.models.user import User


def _create_employee_with_entries(db_session, auth_headers, client, entries_data=None):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Lohn", "last_name": "Mitarbeiter"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    user = db_session.query(User).filter(User.id.isnot(None)).first()
    if user:
        user.employee_id = emp_id
        db_session.add(user)
        db_session.commit()

    if entries_data:
        for ed in entries_data:
            entry = TimeEntry(
                employee_id=emp_id,
                clock_in=ed["clock_in"],
                clock_out=ed["clock_out"],
                duration_minutes=ed["duration_minutes"],
            )
            db_session.add(entry)
        db_session.commit()

    return emp_id


class TestPayrollCsvExport:
    def test_requires_auth(self, client):
        r = client.get(
            "/api/v1/payroll/csv",
            params={"employee_id": 1, "start_date": "2026-07-06", "end_date": "2026-07-12"},
        )
        assert r.status_code in (401, 403)

    def test_csv_export_success(self, client, auth_headers, db_session):
        emp_id = _create_employee_with_entries(db_session, auth_headers, client)
        start = datetime(2026, 7, 6, 8, 0, tzinfo=timezone.utc)
        entry = TimeEntry(
            employee_id=emp_id,
            clock_in=start,
            clock_out=start + timedelta(hours=8),
            duration_minutes=480,
        )
        db_session.add(entry)
        db_session.commit()

        r = client.get(
            "/api/v1/payroll/csv",
            params={"employee_id": emp_id, "start_date": "2026-07-06", "end_date": "2026-07-12"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert "attachment" in r.headers.get("content-disposition", "")
        assert r.content[:3] == b"\xef\xbb\xbf"

    def test_csv_column_order(self, client, auth_headers, db_session):
        emp_id = _create_employee_with_entries(db_session, auth_headers, client)
        start = datetime(2026, 7, 6, 10, 0, tzinfo=timezone.utc)
        entry = TimeEntry(
            employee_id=emp_id,
            clock_in=start,
            clock_out=start + timedelta(hours=8),
            duration_minutes=480,
        )
        db_session.add(entry)
        db_session.commit()

        r = client.get(
            "/api/v1/payroll/csv",
            params={"employee_id": emp_id, "start_date": "2026-07-06", "end_date": "2026-07-12"},
            headers=auth_headers,
        )
        import csv
        import io
        csv_text = r.content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(csv_text))
        header = next(reader)
        assert header == [
            "Datum", "Kalenderwoche", "Wochentag", "Schichttyp",
            "Beginn", "Ende", "Dauer_Stunden", "Ueberstunden", "Notizen",
        ]

    def test_400_end_date_before_start_date(self, client, auth_headers, db_session):
        emp_id = _create_employee_with_entries(db_session, auth_headers, client)
        r = client.get(
            "/api/v1/payroll/csv",
            params={"employee_id": emp_id, "start_date": "2026-07-12", "end_date": "2026-07-06"},
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_400_range_exceeds_one_year(self, client, auth_headers, db_session):
        emp_id = _create_employee_with_entries(db_session, auth_headers, client)
        r = client.get(
            "/api/v1/payroll/csv",
            params={"employee_id": emp_id, "start_date": "2026-01-01", "end_date": "2027-01-02"},
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_404_unknown_employee(self, client, auth_headers):
        r = client.get(
            "/api/v1/payroll/csv",
            params={"employee_id": 99999, "start_date": "2026-07-06", "end_date": "2026-07-12"},
            headers=auth_headers,
        )
        assert r.status_code == 404

    def test_403_non_admin_other_employee(self, client, employee_auth_headers, db_session):
        headers, emp_id = employee_auth_headers
        other_emp = Employee(first_name="Other", last_name="Employee")
        db_session.add(other_emp)
        db_session.commit()
        db_session.refresh(other_emp)

        r = client.get(
            "/api/v1/payroll/csv",
            params={"employee_id": other_emp.id, "start_date": "2026-07-06", "end_date": "2026-07-12"},
            headers=headers,
        )
        assert r.status_code == 403

    def test_non_admin_can_export_self(self, client, employee_auth_headers, db_session):
        headers, emp_id = employee_auth_headers
        start = datetime(2026, 7, 6, 8, 0, tzinfo=timezone.utc)
        entry = TimeEntry(
            employee_id=emp_id,
            clock_in=start,
            clock_out=start + timedelta(hours=8),
            duration_minutes=480,
        )
        db_session.add(entry)
        db_session.commit()

        r = client.get(
            "/api/v1/payroll/csv",
            params={"employee_id": emp_id, "start_date": "2026-07-06", "end_date": "2026-07-12"},
            headers=headers,
        )
        assert r.status_code == 200

    def test_empty_entries_csv(self, client, auth_headers, db_session):
        emp_id = _create_employee_with_entries(db_session, auth_headers, client)
        r = client.get(
            "/api/v1/payroll/csv",
            params={"employee_id": emp_id, "start_date": "2026-07-06", "end_date": "2026-07-12"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        csv_text = r.content.decode("utf-8-sig")
        lines = csv_text.strip().split("\n")
        assert len(lines) == 3  # header + week summary + total summary

    def test_missing_required_params(self, client, auth_headers):
        r = client.get("/api/v1/payroll/csv", headers=auth_headers)
        assert r.status_code == 422
