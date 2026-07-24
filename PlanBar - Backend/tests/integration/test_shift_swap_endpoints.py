def _create_schedule_and_shifts(client, admin_headers, emp_id, target_emp_id, prefix="Test"):
    sched_resp = client.post(
        "/api/v1/schedules",
        json={"name": f"{prefix} Schedule", "start_date": "2026-07-01", "end_date": "2026-07-31"},
        headers=admin_headers,
    )
    schedule_id = sched_resp.json()["id"]

    shift_resp = client.put(
        f"/api/v1/schedules/{schedule_id}/shifts",
        json={
            "shiftplans": [
                {
                    "employee_id": emp_id,
                    "date": "2026-07-06",
                    "shift_id": "morning",
                    "start_time": "08:00:00",
                    "end_time": "16:00:00",
                },
                {
                    "employee_id": target_emp_id,
                    "date": "2026-07-07",
                    "shift_id": "evening",
                    "start_time": "14:00:00",
                    "end_time": "22:00:00",
                },
            ]
        },
        headers=admin_headers,
    )
    data = shift_resp.json()
    requester_shift_id = None
    target_shift_id = None
    for sp in data["shiftplans"]:
        if sp["employee_id"] == emp_id:
            requester_shift_id = sp["id"]
        else:
            target_shift_id = sp["id"]
    return schedule_id, requester_shift_id, target_shift_id


def test_create_shift_swap(client, auth_headers, employee_auth_headers):
    admin_headers = auth_headers
    emp_headers, emp_id = employee_auth_headers

    target_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Target", "last_name": "Employee"},
        headers=admin_headers,
    )
    target_emp_id = target_resp.json()["id"]

    _, requester_shift_id, target_shift_id = _create_schedule_and_shifts(client, admin_headers, emp_id, target_emp_id)

    response = client.post(
        "/api/v1/shift-swaps",
        json={
            "requester_shift_id": requester_shift_id,
            "target_employee_id": target_emp_id,
            "target_shift_id": target_shift_id,
            "note": "Can we swap?",
        },
        headers=emp_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["employee_id"] == emp_id
    assert data["target_employee_id"] == target_emp_id
    assert data["status"] == "pending"
    assert data["note"] == "Can we swap?"


def test_create_shift_swap_wrong_shift(client, employee_auth_headers):
    emp_headers, _emp_id = employee_auth_headers

    response = client.post(
        "/api/v1/shift-swaps",
        json={
            "requester_shift_id": 99999,
            "target_employee_id": 1,
            "target_shift_id": 99998,
        },
        headers=emp_headers,
    )
    assert response.status_code == 404


def test_get_my_shift_swaps(client, employee_auth_headers):
    emp_headers, _emp_id = employee_auth_headers

    response = client.get("/api/v1/shift-swaps/me", headers=emp_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_approve_shift_swap(client, auth_headers, employee_auth_headers):
    admin_headers = auth_headers
    emp_headers, emp_id = employee_auth_headers

    target_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Target2", "last_name": "Employee"},
        headers=admin_headers,
    )
    target_emp_id = target_resp.json()["id"]

    _, requester_shift_id, target_shift_id = _create_schedule_and_shifts(
        client, admin_headers, emp_id, target_emp_id, prefix="Swap"
    )

    create_resp = client.post(
        "/api/v1/shift-swaps",
        json={
            "requester_shift_id": requester_shift_id,
            "target_employee_id": target_emp_id,
            "target_shift_id": target_shift_id,
        },
        headers=emp_headers,
    )
    swap_id = create_resp.json()["id"]

    response = client.put(f"/api/v1/shift-swaps/{swap_id}/approve", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"


def test_reject_shift_swap(client, auth_headers, employee_auth_headers):
    admin_headers = auth_headers
    emp_headers, emp_id = employee_auth_headers

    target_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Target3", "last_name": "Employee"},
        headers=admin_headers,
    )
    target_emp_id = target_resp.json()["id"]

    _, requester_shift_id, target_shift_id = _create_schedule_and_shifts(
        client, admin_headers, emp_id, target_emp_id, prefix="Reject"
    )

    create_resp = client.post(
        "/api/v1/shift-swaps",
        json={
            "requester_shift_id": requester_shift_id,
            "target_employee_id": target_emp_id,
            "target_shift_id": target_shift_id,
        },
        headers=emp_headers,
    )
    swap_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/shift-swaps/{swap_id}/reject",
        json={"rejection_reason": "Not needed"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["rejection_reason"] == "Not needed"


def test_non_admin_cannot_approve_swap(client, employee_auth_headers):
    emp_headers, _emp_id = employee_auth_headers

    response = client.put("/api/v1/shift-swaps/1/approve", headers=emp_headers)
    assert response.status_code == 403


def test_non_admin_cannot_reject_swap(client, employee_auth_headers):
    emp_headers, _emp_id = employee_auth_headers

    response = client.put(
        "/api/v1/shift-swaps/1/reject",
        json={},
        headers=emp_headers,
    )
    assert response.status_code == 403
