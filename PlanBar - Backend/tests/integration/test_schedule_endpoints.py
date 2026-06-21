def test_create_schedule(client, auth_headers):
    response = client.post(
        "/api/v1/schedules",
        json={"name": "Week 23 Schedule", "week_type": "A"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Week 23 Schedule"
    assert data["status"] == "draft"
    assert data["week_type"] == "A"


def test_list_schedules(client, auth_headers):
    response = client.get("/api/v1/schedules", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_schedule(client, auth_headers):
    create_resp = client.post(
        "/api/v1/schedules",
        json={"name": "Test Schedule"},
        headers=auth_headers,
    )
    schedule_id = create_resp.json()["id"]

    response = client.get(f"/api/v1/schedules/{schedule_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Test Schedule"


def test_update_schedule(client, auth_headers):
    create_resp = client.post(
        "/api/v1/schedules",
        json={"name": "Original Name"},
        headers=auth_headers,
    )
    schedule_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/schedules/{schedule_id}",
        json={"name": "Updated Name"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_delete_schedule(client, auth_headers):
    create_resp = client.post(
        "/api/v1/schedules",
        json={"name": "To Delete"},
        headers=auth_headers,
    )
    schedule_id = create_resp.json()["id"]

    response = client.delete(f"/api/v1/schedules/{schedule_id}", headers=auth_headers)
    assert response.status_code == 204


def test_get_schedule_summary(client, auth_headers):
    create_resp = client.post(
        "/api/v1/schedules",
        json={"name": "Summary Test"},
        headers=auth_headers,
    )
    schedule_id = create_resp.json()["id"]

    response = client.get(f"/api/v1/schedules/{schedule_id}/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Summary Test"
    assert data["total_shifts"] == 0


def test_get_schedule_shifts(client, auth_headers):
    create_resp = client.post(
        "/api/v1/schedules",
        json={"name": "Shifts Test"},
        headers=auth_headers,
    )
    schedule_id = create_resp.json()["id"]

    response = client.get(f"/api/v1/schedules/{schedule_id}/shifts", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_schedule_not_found(client, auth_headers):
    response = client.get("/api/v1/schedules/99999", headers=auth_headers)
    assert response.status_code == 404


def test_update_schedule_not_found(client, auth_headers):
    response = client.put("/api/v1/schedules/99999", json={"name": "Nope"}, headers=auth_headers)
    assert response.status_code == 404


def test_delete_schedule_not_found(client, auth_headers):
    response = client.delete("/api/v1/schedules/99999", headers=auth_headers)
    assert response.status_code == 404


def test_submit_schedule_not_found(client, auth_headers):
    response = client.post("/api/v1/schedules/99999/submit", headers=auth_headers)
    assert response.status_code == 404


def test_retry_schedule_not_found(client, auth_headers):
    response = client.post("/api/v1/schedules/99999/retry", headers=auth_headers)
    assert response.status_code == 404


def test_summary_not_found(client, auth_headers):
    response = client.get("/api/v1/schedules/99999/summary", headers=auth_headers)
    assert response.status_code == 404


def test_get_shifts_not_found(client, auth_headers):
    response = client.get("/api/v1/schedules/99999/shifts", headers=auth_headers)
    assert response.status_code == 404


def test_update_shiftplan(client, auth_headers):
    create_resp = client.post(
        "/api/v1/schedules",
        json={
            "name": "Shiftplan Test",
            "start_date": "2026-06-01",
            "end_date": "2026-06-07",
        },
        headers=auth_headers,
    )
    schedule_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/schedules/{schedule_id}/shifts",
        json={
            "shiftplans": [
                {
                    "employee_id": 1,
                    "date": "2026-06-01",
                    "shift_id": "früh",
                    "start_time": "06:00",
                    "end_time": "14:00",
                },
            ]
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["shiftplans"]) == 1


def test_update_shiftplan_not_found(client, auth_headers):
    response = client.put(
        "/api/v1/schedules/99999/shifts/1",
        json={"shift_id": "spät", "start_time": "14:00", "end_time": "22:00"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_replace_all_shifts_not_found(client, auth_headers):
    response = client.put(
        "/api/v1/schedules/99999/shifts",
        json={"shiftplans": []},
        headers=auth_headers,
    )
    assert response.status_code == 404
