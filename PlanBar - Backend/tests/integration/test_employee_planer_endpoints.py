"""Integration tests for planer RBAC on /api/v1/employees endpoints.

Planners must be able to list/get employees in their teams (so they can plan
shifts), but must NOT modify employee master data, contracts or timecards.
"""


def _create_employee(client, auth_headers, first="X", last="Y"):
    return client.post(
        "/api/v1/employees",
        json={"first_name": first, "last_name": last},
        headers=auth_headers,
    ).json()["id"]


def test_planer_can_list_employees_in_own_team(
    client, auth_headers, planer_auth_headers, planner_team, db_session
):
    own_emp_id = _create_employee(client, auth_headers, "Own", "List")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [own_emp_id]},
        headers=auth_headers,
    )
    _create_employee(client, auth_headers, "Foreign", "List")

    response = client.get("/api/v1/employees", headers=planer_auth_headers)
    assert response.status_code == 200
    names = [e["first_name"] for e in response.json()["items"]]
    assert "Own" in names
    assert "Foreign" not in names


def test_planer_can_get_employee_in_own_team(
    client, auth_headers, planer_auth_headers, planner_team
):
    own_emp_id = _create_employee(client, auth_headers, "Own", "Get")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [own_emp_id]},
        headers=auth_headers,
    )
    response = client.get(f"/api/v1/employees/{own_emp_id}", headers=planer_auth_headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == "Own"


def test_planer_cannot_get_employee_outside_team(
    client, auth_headers, planer_auth_headers
):
    foreign_emp_id = _create_employee(client, auth_headers, "Foreign", "Get")
    response = client.get(
        f"/api/v1/employees/{foreign_emp_id}", headers=planer_auth_headers
    )
    assert response.status_code == 403


def test_planer_cannot_create_employee(client, planer_auth_headers):
    response = client.post(
        "/api/v1/employees",
        json={"first_name": "X", "last_name": "Y"},
        headers=planer_auth_headers,
    )
    assert response.status_code == 403


def test_planer_cannot_update_employee(
    client, auth_headers, planer_auth_headers, planner_team
):
    own_emp_id = _create_employee(client, auth_headers, "Own", "Update")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [own_emp_id]},
        headers=auth_headers,
    )
    response = client.put(
        f"/api/v1/employees/{own_emp_id}",
        json={"first_name": "Hacked"},
        headers=planer_auth_headers,
    )
    assert response.status_code == 403


def test_planer_cannot_delete_employee(
    client, auth_headers, planer_auth_headers, planner_team
):
    own_emp_id = _create_employee(client, auth_headers, "Own", "Delete")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [own_emp_id]},
        headers=auth_headers,
    )
    response = client.delete(
        f"/api/v1/employees/{own_emp_id}", headers=planer_auth_headers
    )
    assert response.status_code == 403


def test_planer_cannot_manage_contracts(client, planer_auth_headers):
    response = client.get("/api/v1/contracts", headers=planer_auth_headers)
    assert response.status_code == 403


def test_planer_cannot_manage_timecards(client, planer_auth_headers):
    response = client.get("/api/v1/timecards", headers=planer_auth_headers)
    assert response.status_code == 403


def test_employee_can_still_only_see_self(client, employee_auth_headers):
    headers, _ = employee_auth_headers
    response = client.get("/api/v1/employees", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1