def test_create_employee(client, auth_headers):
    response = client.post(
        "/api/v1/employees",
        json={"first_name": "John", "last_name": "Doe"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["id"] is not None


def test_list_employees(client, auth_headers):
    client.post(
        "/api/v1/employees",
        json={"first_name": "Jane", "last_name": "Smith"},
        headers=auth_headers,
    )
    response = client.get("/api/v1/employees", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert any(e["first_name"] == "Jane" for e in data["items"])


def test_get_employee(client, auth_headers):
    create_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Bob", "last_name": "Wilson"},
        headers=auth_headers,
    )
    emp_id = create_resp.json()["id"]

    response = client.get(f"/api/v1/employees/{emp_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == "Bob"


def test_update_employee(client, auth_headers):
    create_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Alice", "last_name": "Brown"},
        headers=auth_headers,
    )
    emp_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"first_name": "Alicia"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["first_name"] == "Alicia"


def test_delete_employee(client, auth_headers):
    create_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Charlie", "last_name": "Delete"},
        headers=auth_headers,
    )
    emp_id = create_resp.json()["id"]

    response = client.delete(f"/api/v1/employees/{emp_id}", headers=auth_headers)
    assert response.status_code == 204

    get_resp = client.get(f"/api/v1/employees/{emp_id}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_get_employee_not_found(client, auth_headers):
    response = client.get("/api/v1/employees/99999", headers=auth_headers)
    assert response.status_code == 404


def test_update_employee_not_found(client, auth_headers):
    response = client.put("/api/v1/employees/99999", json={"first_name": "Nope"}, headers=auth_headers)
    assert response.status_code == 404


def test_delete_employee_not_found(client, auth_headers):
    response = client.delete("/api/v1/employees/99999", headers=auth_headers)
    assert response.status_code == 404


def test_get_contract_not_found(client, auth_headers):
    response = client.get("/api/v1/contracts/99999", headers=auth_headers)
    assert response.status_code == 404


def test_update_contract_not_found(client, auth_headers):
    response = client.put(
        "/api/v1/contracts/99999",
        json={"weekly_working_hours": 35},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_get_timecard_not_found(client, auth_headers):
    response = client.get("/api/v1/timecards/99999", headers=auth_headers)
    assert response.status_code == 404


def test_update_timecard(client, auth_headers):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "TCUpd", "last_name": "Test"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]
    create_resp = client.post(
        "/api/v1/timecards",
        json={"employee_id": emp_id, "week": 20, "year": 2026, "balance": 5.0},
        headers=auth_headers,
    )
    tc_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/timecards/{tc_id}",
        json={"balance": 10.0},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["balance"] == 10.0


def test_update_timecard_not_found(client, auth_headers):
    response = client.put("/api/v1/timecards/99999", json={"balance": 10.0}, headers=auth_headers)
    assert response.status_code == 404


def test_update_contract(client, auth_headers):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "CUpdInt", "last_name": "Test"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]
    create_resp = client.post(
        "/api/v1/contracts",
        json={"employee_id": emp_id, "weekly_working_hours": 40, "break_time": 30},
        headers=auth_headers,
    )
    contract_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/contracts/{contract_id}",
        json={"weekly_working_hours": 35, "hired_role": "supervisor"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["weekly_working_hours"] == 35


def test_create_contract(client, auth_headers):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Contract", "last_name": "Test"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    response = client.post(
        "/api/v1/contracts",
        json={"employee_id": emp_id, "weekly_working_hours": 40, "break_time": 30},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["weekly_working_hours"] == 40
    assert data["break_time"] == 30


def test_list_contracts(client, auth_headers):
    response = client.get("/api/v1/contracts", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_create_timecard(client, auth_headers):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Timecard", "last_name": "Test"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    response = client.post(
        "/api/v1/timecards",
        json={"employee_id": emp_id, "week": 20, "year": 2026, "balance": 10.5},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["week"] == 20
    assert data["year"] == 2026
    assert data["balance"] == 10.5


def test_list_timecards(client, auth_headers):
    response = client.get("/api/v1/timecards", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)


# --- ArbZG-relevant employee fields (is_minor, is_night_worker, ...) ---


def test_create_employee_with_arbzg_fields(client, auth_headers):
    """Neue ArbZG-Felder müssen beim Anlegen mitgegeben und zurückgegeben werden."""
    response = client.post(
        "/api/v1/employees",
        json={
            "first_name": "Mia",
            "last_name": "Minor",
            "is_minor": True,
            "is_night_worker": True,
            "is_shift_worker": True,
            "night_worker_exam_date": "2026-02-01",
            "protection_until": "2026-06-30",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["is_minor"] is True
    assert data["is_night_worker"] is True
    assert data["is_shift_worker"] is True
    assert data["night_worker_exam_date"] == "2026-02-01"
    assert data["protection_until"] == "2026-06-30"


def test_create_employee_arbzg_defaults(client, auth_headers):
    """Ohne explizite Angaben gelten die Defaults (False/None)."""
    response = client.post(
        "/api/v1/employees",
        json={"first_name": "Default", "last_name": "Arbzg"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["is_minor"] is False
    assert data["is_night_worker"] is False
    assert data["is_shift_worker"] is False
    assert data["night_worker_exam_date"] is None
    assert data["protection_until"] is None


def test_update_employee_arbzg_fields(client, auth_headers):
    """Updates müssen die ArbZG-Felder tragen (inkl. explizites Zurücksetzen auf False)."""
    create_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Upd", "last_name": "Arbzg"},
        headers=auth_headers,
    )
    emp_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"is_minor": True, "is_night_worker": True, "night_worker_exam_date": "2026-03-01"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_minor"] is True
    assert data["is_night_worker"] is True
    assert data["night_worker_exam_date"] == "2026-03-01"

    # Minderjährigkeit endet: explizit auf False zurücksetzen
    response = client.put(
        f"/api/v1/employees/{emp_id}",
        json={"is_minor": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_minor"] is False
    # andere Felder bleiben unangetastet (None = keine Änderung)
    assert response.json()["is_night_worker"] is True
