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
    assert len(data) >= 1
    assert any(e["first_name"] == "Jane" for e in data)


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
    assert isinstance(response.json(), list)


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
    assert isinstance(response.json(), list)
