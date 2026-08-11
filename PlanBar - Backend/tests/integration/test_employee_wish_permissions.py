def test_employee_creates_own_shift_wish(client, employee_auth_headers):
    headers, emp_id = employee_auth_headers
    response = client.post(
        "/api/v1/requests",
        json={
            "employee_id": emp_id,
            "date": "2026-06-01",
            "type": "preferred",
            "note": "Morning shift please",
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["employee_id"] == emp_id
    assert data["date"] == "2026-06-01"


def test_employee_cannot_create_wish_for_other(client, employee_auth_headers, auth_headers):
    headers, _ = employee_auth_headers
    other_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Other", "last_name": "Employee"},
        headers=auth_headers,
    )
    other_emp_id = other_resp.json()["id"]

    response = client.post(
        "/api/v1/requests",
        json={
            "employee_id": other_emp_id,
            "date": "2026-06-02",
            "type": "preferred",
        },
        headers=headers,
    )
    assert response.status_code == 403


def test_employee_updates_own_shift_wish(client, employee_auth_headers, auth_headers):
    headers, emp_id = employee_auth_headers
    create_resp = client.post(
        "/api/v1/requests",
        json={
            "employee_id": emp_id,
            "date": "2026-06-03",
            "type": "preferred",
        },
        headers=auth_headers,
    )
    wish_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/requests/{wish_id}",
        json={"note": "Updated by employee"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["note"] == "Updated by employee"


def test_employee_cannot_update_others_wish(client, employee_auth_headers, auth_headers):
    headers, _ = employee_auth_headers
    other_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Other2", "last_name": "Employee"},
        headers=auth_headers,
    )
    other_emp_id = other_resp.json()["id"]

    create_resp = client.post(
        "/api/v1/requests",
        json={
            "employee_id": other_emp_id,
            "date": "2026-06-04",
            "type": "preferred",
        },
        headers=auth_headers,
    )
    other_wish_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/requests/{other_wish_id}",
        json={"note": "Hacked!"},
        headers=headers,
    )
    assert response.status_code == 403


def test_employee_deletes_own_shift_wish(client, employee_auth_headers, auth_headers):
    headers, emp_id = employee_auth_headers
    create_resp = client.post(
        "/api/v1/requests",
        json={
            "employee_id": emp_id,
            "date": "2026-06-05",
            "type": "preferred",
        },
        headers=auth_headers,
    )
    wish_id = create_resp.json()["id"]

    response = client.delete(
        f"/api/v1/requests/{wish_id}",
        headers=headers,
    )
    assert response.status_code == 204


def test_employee_cannot_delete_others_wish(client, employee_auth_headers, auth_headers):
    headers, _ = employee_auth_headers
    other_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Other3", "last_name": "Employee"},
        headers=auth_headers,
    )
    other_emp_id = other_resp.json()["id"]

    create_resp = client.post(
        "/api/v1/requests",
        json={
            "employee_id": other_emp_id,
            "date": "2026-06-06",
            "type": "preferred",
        },
        headers=auth_headers,
    )
    other_wish_id = create_resp.json()["id"]

    response = client.delete(
        f"/api/v1/requests/{other_wish_id}",
        headers=headers,
    )
    assert response.status_code == 403
