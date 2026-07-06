def test_create_role(client, auth_headers):
    response = client.post(
        "/api/v1/roles",
        json={"name": "supervisor", "permissions": "all"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "supervisor"
    assert data["permissions"] == "all"


def test_create_duplicate_role(client, auth_headers):
    client.post(
        "/api/v1/roles",
        json={"name": "manager"},
        headers=auth_headers,
    )
    response = client.post(
        "/api/v1/roles",
        json={"name": "manager"},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_list_roles(client, auth_headers):
    response = client.get("/api/v1/roles", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_update_role(client, auth_headers):
    create_resp = client.post(
        "/api/v1/roles",
        json={"name": "editor"},
        headers=auth_headers,
    )
    role_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/roles/{role_id}",
        json={"name": "senior_editor"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "senior_editor"


def test_delete_role(client, auth_headers):
    create_resp = client.post(
        "/api/v1/roles",
        json={"name": "temporary"},
        headers=auth_headers,
    )
    role_id = create_resp.json()["id"]

    response = client.delete(f"/api/v1/roles/{role_id}", headers=auth_headers)
    assert response.status_code == 204
