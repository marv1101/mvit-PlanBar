"""Integration tests for planer RBAC on /api/v1/requests (shift wishes)."""


def _create_employee(client, auth_headers, first, last):
    return client.post(
        "/api/v1/employees",
        json={"first_name": first, "last_name": last},
        headers=auth_headers,
    ).json()["id"]


def test_planer_can_list_team_wishes(client, auth_headers, planer_auth_headers, planner_team, db_session):
    own_emp_id = _create_employee(client, auth_headers, "Own", "Wish")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [own_emp_id]},
        headers=auth_headers,
    )

    # Create a wish for own team employee
    wish_resp = client.post(
        "/api/v1/requests",
        json={"employee_id": own_emp_id, "date": "2026-07-01", "type": "preferred"},
        headers=auth_headers,
    )
    assert wish_resp.status_code == 201
    wish_id = wish_resp.json()["id"]

    foreign_emp_id = _create_employee(client, auth_headers, "Foreign", "Wish")
    foreign_wish_resp = client.post(
        "/api/v1/requests",
        json={"employee_id": foreign_emp_id, "date": "2026-07-02", "type": "preferred"},
        headers=auth_headers,
    )
    assert foreign_wish_resp.status_code == 201

    response = client.get("/api/v1/requests", headers=planer_auth_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    wish_ids = [w["id"] for w in items]
    assert wish_id in wish_ids
    assert foreign_wish_resp.json()["id"] not in wish_ids


def test_planer_can_approve_team_wish(client, auth_headers, planer_auth_headers, planner_team):
    own_emp_id = _create_employee(client, auth_headers, "Own", "Approve")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [own_emp_id]},
        headers=auth_headers,
    )
    wish_resp = client.post(
        "/api/v1/requests",
        json={"employee_id": own_emp_id, "date": "2026-07-01", "type": "preferred"},
        headers=auth_headers,
    )
    wish_id = wish_resp.json()["id"]

    response = client.put(f"/api/v1/requests/{wish_id}/approve", headers=planer_auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_planer_cannot_approve_foreign_wish(client, auth_headers, planer_auth_headers):
    foreign_emp_id = _create_employee(client, auth_headers, "Foreign", "Approve")
    wish_resp = client.post(
        "/api/v1/requests",
        json={"employee_id": foreign_emp_id, "date": "2026-07-01", "type": "preferred"},
        headers=auth_headers,
    )
    wish_id = wish_resp.json()["id"]

    response = client.put(f"/api/v1/requests/{wish_id}/approve", headers=planer_auth_headers)
    assert response.status_code == 403


def test_planer_can_create_wish_for_team_member(client, auth_headers, planer_auth_headers, planner_team):
    own_emp_id = _create_employee(client, auth_headers, "Own", "Create")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [own_emp_id]},
        headers=auth_headers,
    )
    response = client.post(
        "/api/v1/requests",
        json={"employee_id": own_emp_id, "date": "2026-07-01", "type": "preferred"},
        headers=planer_auth_headers,
    )
    assert response.status_code == 201


def test_planer_cannot_create_wish_for_foreign_employee(client, auth_headers, planer_auth_headers):
    foreign_emp_id = _create_employee(client, auth_headers, "Foreign", "Create")
    response = client.post(
        "/api/v1/requests",
        json={"employee_id": foreign_emp_id, "date": "2026-07-01", "type": "preferred"},
        headers=planer_auth_headers,
    )
    assert response.status_code == 403


def test_planer_can_update_team_wish_status(client, auth_headers, planer_auth_headers, planner_team):
    own_emp_id = _create_employee(client, auth_headers, "Own", "Update")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [own_emp_id]},
        headers=auth_headers,
    )
    wish_resp = client.post(
        "/api/v1/requests",
        json={"employee_id": own_emp_id, "date": "2026-07-01", "type": "preferred"},
        headers=auth_headers,
    )
    wish_id = wish_resp.json()["id"]

    response = client.put(
        f"/api/v1/requests/{wish_id}",
        json={"status": "rejected"},
        headers=planer_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_planer_cannot_update_foreign_wish_status(client, auth_headers, planer_auth_headers):
    foreign_emp_id = _create_employee(client, auth_headers, "Foreign", "Update")
    wish_resp = client.post(
        "/api/v1/requests",
        json={"employee_id": foreign_emp_id, "date": "2026-07-01", "type": "preferred"},
        headers=auth_headers,
    )
    wish_id = wish_resp.json()["id"]

    response = client.put(
        f"/api/v1/requests/{wish_id}",
        json={"status": "approved"},
        headers=planer_auth_headers,
    )
    assert response.status_code == 403


def test_employee_cannot_approve_own_wish(client, employee_auth_headers):
    headers, emp_id = employee_auth_headers
    wish_resp = client.post(
        "/api/v1/requests",
        json={"employee_id": emp_id, "date": "2026-07-01", "type": "preferred"},
        headers=headers,
    )
    wish_id = wish_resp.json()["id"]
    response = client.put(f"/api/v1/requests/{wish_id}/approve", headers=headers)
    assert response.status_code == 403