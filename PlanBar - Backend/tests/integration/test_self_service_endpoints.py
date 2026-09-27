def test_get_my_schedule_no_employee(client, auth_headers):
    """User without linked employee gets empty list."""
    response = client.get("/api/v1/my/schedule", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_my_schedule(client, auth_headers, employee_auth_headers):
    admin_headers = auth_headers
    emp_headers, emp_id = employee_auth_headers

    sched_resp = client.post(
        "/api/v1/schedules",
        json={"name": "My Schedule", "start_date": "2026-07-01", "end_date": "2026-07-07"},
        headers=admin_headers,
    )
    schedule_id = sched_resp.json()["id"]

    client.put(
        f"/api/v1/schedules/{schedule_id}/shifts",
        json={
            "shiftplans": [
                {
                    "employee_id": emp_id,
                    "date": "2026-07-06",
                    "shift_id": "morning",
                    "start_time": "08:00:00",
                    "end_time": "16:00:00",
                    "break_start": "12:00",
                    "break_end": "12:30",
                }
            ]
        },
        headers=admin_headers,
    )

    response = client.get("/api/v1/my/schedule", headers=emp_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["start_time"] == "08:00:00"


def test_get_my_overtime_no_employee(client, auth_headers):
    response = client.get("/api/v1/my/overtime", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["current_balance"] == 0.0


def test_get_my_overtime(client, employee_auth_headers):
    emp_headers, _emp_id = employee_auth_headers

    response = client.get("/api/v1/my/overtime", headers=emp_headers)
    assert response.status_code == 200
    data = response.json()
    assert "current_balance" in data


def test_update_my_availability(client, employee_auth_headers):
    emp_headers, _emp_id = employee_auth_headers

    response = client.put(
        "/api/v1/my/availability",
        json={
            "entries": [
                {"day_of_week": 0, "available": False, "note": "Church"},
                {"day_of_week": 6, "available": False, "note": "Rest"},
            ]
        },
        headers=emp_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["day_of_week"] == 0
    assert data[0]["available"] is False

    get_resp = client.get("/api/v1/my/availability", headers=emp_headers)
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert len(get_data) == 2


def test_update_availability_updates_existing(client, employee_auth_headers):
    emp_headers, _emp_id = employee_auth_headers

    client.put(
        "/api/v1/my/availability",
        json={"entries": [{"day_of_week": 1, "available": True}]},
        headers=emp_headers,
    )

    response = client.put(
        "/api/v1/my/availability",
        json={"entries": [{"day_of_week": 1, "available": False, "note": "Changed"}]},
        headers=emp_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["available"] is False
    assert data[0]["note"] == "Changed"


def test_unauthorized_access_returns_401(client):
    response = client.get("/api/v1/my/schedule")
    assert response.status_code == 401

    response = client.get("/api/v1/shift-swaps/me")
    assert response.status_code == 401
