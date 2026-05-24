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
