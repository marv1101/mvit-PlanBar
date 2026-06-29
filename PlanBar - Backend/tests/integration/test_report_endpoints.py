from datetime import date


def _week_year(d: date) -> tuple[int, int]:
    iso = d.isocalendar()
    return iso[0], iso[1]


def test_overtime_report_all_employees(client, auth_headers):
    emp1 = client.post(
        "/api/v1/employees",
        json={"first_name": "Max", "last_name": "Mustermann"},
        headers=auth_headers,
    ).json()
    emp2 = client.post(
        "/api/v1/employees",
        json={"first_name": "Erika", "last_name": "Musterfrau"},
        headers=auth_headers,
    ).json()

    ref = date(2026, 6, 1)
    y, w = _week_year(ref)

    for emp_id in (emp1["id"], emp2["id"]):
        actual = 45.0 if emp_id == emp1["id"] else 38.0
        balance = 5.0 if emp_id == emp1["id"] else -2.0
        client.post(
            "/api/v1/timecards",
            json={
                "employee_id": emp_id,
                "week": w,
                "year": y,
                "scheduled_hours": 40.0,
                "actual_hours": actual,
                "contract_hours": 40.0,
                "balance": balance,
            },
            headers=auth_headers,
        )

    response = client.get(
        "/api/v1/reports/overtime?start_date=2026-06-01&end_date=2026-06-07",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["employees"]) == 2
    names = {e["employee_name"] for e in data["employees"]}
    assert "Max Mustermann" in names
    assert "Erika Musterfrau" in names
    assert data["summary"]["total_employees"] == 2
    assert data["summary"]["total_overtime_hours"] == 3.0


def test_overtime_report_filter_by_employee(client, auth_headers):
    emp1 = client.post(
        "/api/v1/employees",
        json={"first_name": "Max", "last_name": "Mustermann"},
        headers=auth_headers,
    ).json()
    emp2 = client.post(
        "/api/v1/employees",
        json={"first_name": "Erika", "last_name": "Musterfrau"},
        headers=auth_headers,
    ).json()

    ref = date(2026, 6, 1)
    y, w = _week_year(ref)

    for emp_id in (emp1["id"], emp2["id"]):
        actual = 45.0 if emp_id == emp1["id"] else 38.0
        balance = 5.0 if emp_id == emp1["id"] else -2.0
        client.post(
            "/api/v1/timecards",
            json={
                "employee_id": emp_id,
                "week": w,
                "year": y,
                "scheduled_hours": 40.0,
                "actual_hours": actual,
                "contract_hours": 40.0,
                "balance": balance,
            },
            headers=auth_headers,
        )

    response = client.get(
        f"/api/v1/reports/overtime?employee_id={emp1['id']}&start_date=2026-06-01&end_date=2026-06-07",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["employees"]) == 1
    assert data["employees"][0]["employee_name"] == "Max Mustermann"
    assert data["employees"][0]["overtime_hours"] == 5.0


def test_compliance_rest_period_violation(client, auth_headers):
    emp = client.post(
        "/api/v1/employees",
        json={"first_name": "John", "last_name": "Doe"},
        headers=auth_headers,
    ).json()
    emp_id = emp["id"]

    client.post(
        "/api/v1/schedules",
        json={
            "name": "Rest Period Test",
            "start_date": "2026-06-01",
            "end_date": "2026-06-07",
            "shiftplans": [
                {
                    "employee_id": emp_id,
                    "date": "2026-06-01",
                    "shift_id": "early",
                    "start_time": "13:00",
                    "end_time": "22:00",
                },
                {
                    "employee_id": emp_id,
                    "date": "2026-06-02",
                    "shift_id": "late",
                    "start_time": "06:00",
                    "end_time": "14:00",
                },
            ],
        },
        headers=auth_headers,
    )

    response = client.get(
        "/api/v1/reports/compliance?start_date=2026-06-01&end_date=2026-06-07",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    rest_violations = [v for v in data["violations"] if v["rule"] == "rest_period"]
    assert len(rest_violations) >= 1
    assert rest_violations[0]["employee_name"] == "John Doe"
    assert rest_violations[0]["details"]["actual_rest_hours"] < 11


def test_compliance_max_hours_violation(client, auth_headers):
    emp = client.post(
        "/api/v1/employees",
        json={"first_name": "Jane", "last_name": "Smith"},
        headers=auth_headers,
    ).json()
    emp_id = emp["id"]

    client.post(
        "/api/v1/schedules",
        json={
            "name": "Max Hours Test",
            "start_date": "2026-06-01",
            "end_date": "2026-06-07",
            "shiftplans": [
                {
                    "employee_id": emp_id,
                    "date": "2026-06-01",
                    "shift_id": "long",
                    "start_time": "06:00",
                    "end_time": "20:00",
                },
            ],
        },
        headers=auth_headers,
    )

    response = client.get(
        "/api/v1/reports/compliance?start_date=2026-06-01&end_date=2026-06-07",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    max_violations = [v for v in data["violations"] if v["rule"] == "max_hours"]
    assert len(max_violations) >= 1
    assert max_violations[0]["employee_name"] == "Jane Smith"
    assert max_violations[0]["details"]["actual_hours"] > 10


def test_pdf_export_overtime(client, auth_headers):
    emp = client.post(
        "/api/v1/employees",
        json={"first_name": "PDF", "last_name": "Test"},
        headers=auth_headers,
    ).json()

    ref = date(2026, 6, 1)
    y, w = _week_year(ref)
    client.post(
        "/api/v1/timecards",
        json={
            "employee_id": emp["id"],
            "week": w,
            "year": y,
            "scheduled_hours": 40.0,
            "actual_hours": 45.0,
            "contract_hours": 40.0,
            "balance": 5.0,
        },
        headers=auth_headers,
    )

    response = client.get(
        "/api/v1/reports/overtime/pdf?start_date=2026-06-01&end_date=2026-06-07",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:5] == b"%PDF-"


def test_pdf_export_compliance(client, auth_headers):
    emp = client.post(
        "/api/v1/employees",
        json={"first_name": "PDF", "last_name": "Compliance"},
        headers=auth_headers,
    ).json()

    client.post(
        "/api/v1/schedules",
        json={
            "name": "PDF Compliance Test",
            "start_date": "2026-06-01",
            "end_date": "2026-06-07",
            "shiftplans": [
                {
                    "employee_id": emp["id"],
                    "date": "2026-06-01",
                    "shift_id": "test",
                    "start_time": "08:00",
                    "end_time": "17:00",
                },
            ],
        },
        headers=auth_headers,
    )

    response = client.get(
        "/api/v1/reports/compliance/pdf?start_date=2026-06-01&end_date=2026-06-07",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:5] == b"%PDF-"


def test_reports_require_admin(client, employee_auth_headers):
    headers, _ = employee_auth_headers
    for path in ("/overtime", "/compliance", "/overtime/pdf", "/compliance/pdf"):
        response = client.get(f"/api/v1/reports{path}", headers=headers)
        assert response.status_code == 403, f"{path} should return 403 for non-admin"
