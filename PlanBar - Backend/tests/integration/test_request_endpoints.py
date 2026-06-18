def test_create_shift_wish(client, auth_headers):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Wish", "last_name": "User"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    response = client.post(
        "/api/v1/requests",
        json={
            "employee_id": emp_id,
            "date": "2026-06-01",
            "week": 23,
            "type": "preferred",
            "note": "I prefer morning shifts",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["employee_id"] == emp_id
    assert data["date"] == "2026-06-01"
    assert data["type"] == "preferred"


def test_list_shift_wishes(client, auth_headers):
    response = client.get("/api/v1/requests", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_shift_wish(client, auth_headers):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Get", "last_name": "Wish"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    create_resp = client.post(
        "/api/v1/requests",
        json={"employee_id": emp_id, "date": "2026-06-02", "type": "unavailable"},
        headers=auth_headers,
    )
    wish_id = create_resp.json()["id"]

    response = client.get(f"/api/v1/requests/{wish_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["type"] == "unavailable"


def test_update_shift_wish(client, auth_headers):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Update", "last_name": "Wish"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    create_resp = client.post(
        "/api/v1/requests",
        json={"employee_id": emp_id, "date": "2026-06-03", "type": "preferred"},
        headers=auth_headers,
    )
    wish_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/requests/{wish_id}",
        json={"note": "Updated note"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["note"] == "Updated note"


def test_delete_shift_wish(client, auth_headers):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Delete", "last_name": "Wish"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    create_resp = client.post(
        "/api/v1/requests",
        json={"employee_id": emp_id, "date": "2026-06-04", "type": "preferred"},
        headers=auth_headers,
    )
    wish_id = create_resp.json()["id"]

    response = client.delete(f"/api/v1/requests/{wish_id}", headers=auth_headers)
    assert response.status_code == 204


def test_create_wish_ignores_status_field(client, employee_auth_headers):
    """Non-admin users cannot bypass approval workflow by setting status='approved'."""
    emp_headers, emp_id = employee_auth_headers

    response = client.post(
        "/api/v1/requests",
        json={
            "employee_id": emp_id,
            "date": "2026-06-10",
            "type": "preferred",
            "status": "approved",
        },
        headers=emp_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending", f"Expected status 'pending', got '{data['status']}'"


def test_create_wish_default_status_is_pending(client, employee_auth_headers):
    """New wishes default to 'pending' status without explicit status field."""
    emp_headers, emp_id = employee_auth_headers

    response = client.post(
        "/api/v1/requests",
        json={
            "employee_id": emp_id,
            "date": "2026-06-11",
            "type": "preferred",
        },
        headers=emp_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending", f"Expected status 'pending', got '{data['status']}'"


def test_non_admin_cannot_update_status(client, employee_auth_headers):
    """Non-admin users cannot change status via update endpoint."""
    emp_headers, emp_id = employee_auth_headers

    create_resp = client.post(
        "/api/v1/requests",
        json={"employee_id": emp_id, "date": "2026-06-12", "type": "preferred"},
        headers=emp_headers,
    )
    wish_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/requests/{wish_id}",
        json={"status": "approved"},
        headers=emp_headers,
    )
    assert response.status_code == 403
