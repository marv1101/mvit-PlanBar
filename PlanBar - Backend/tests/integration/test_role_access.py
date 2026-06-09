"""Integration tests for role-based access control."""

import uuid


def _create_user(client, password="password123"):
    email = f"{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/api/v1/users",
        json={
            "username": email.split("@")[0],
            "email": email,
            "password": password,
        },
    )
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["id"]
    login_resp = client.post(
        "/api/v1/users/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    return token, user_id


def test_non_admin_cannot_list_users(client):
    token, _ = _create_user(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/users", headers=headers)
    assert response.status_code == 403


def test_non_admin_cannot_delete_user(client):
    token, _ = _create_user(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.delete("/api/v1/users/1", headers=headers)
    assert response.status_code == 403


def test_non_admin_cannot_admin_create(client):
    token, _ = _create_user(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/users/admin-create",
        json={"username": "shouldfail", "email": "fail@example.com"},
        headers=headers,
    )
    assert response.status_code == 403


def test_non_admin_can_read_self(client):
    token, user_id = _create_user(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert response.status_code == 200


def test_non_admin_cannot_read_other_user(client):
    token, _ = _create_user(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/users/1", headers=headers)
    assert response.status_code in (401, 403)


def test_non_admin_can_update_self(client):
    token, user_id = _create_user(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.put(
        f"/api/v1/users/{user_id}",
        json={"username": "updatedregular"},
        headers=headers,
    )
    assert response.status_code == 200


def test_non_admin_cannot_update_other_user(client):
    token, _ = _create_user(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.put(
        "/api/v1/users/1",
        json={"username": "hacked"},
        headers=headers,
    )
    assert response.status_code in (401, 403)


def test_admin_can_delete_user(client, auth_headers):
    # re-use the same pattern as test_users.py::test_delete_user_by_id
    create_resp = client.post(
        "/api/v1/users",
        json={"username": "admindel", "email": "admindel@example.com", "password": "password123"},
    )
    assert create_resp.status_code == 201, create_resp.text
    user_id = create_resp.json()["id"]

    response = client.delete(f"/api/v1/users/{user_id}", headers=auth_headers)
    assert response.status_code == 204, response.text


def test_admin_can_list_users(client, auth_headers):
    response = client.get("/api/v1/users", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_admin_can_read_any_user(client, auth_headers):
    response = client.get("/api/v1/users/1", headers=auth_headers)
    assert response.status_code == 200


def test_non_admin_cannot_self_promote_to_admin(client):
    """Regression test: non-admin user must not be able to change their own role to admin."""
    token, user_id = _create_user(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.put(
        f"/api/v1/users/{user_id}",
        json={"role": "admin"},
        headers=headers,
    )
    assert response.status_code in (401, 403), response.text
    assert "Only admins can change user roles" in response.json()["detail"]


def test_admin_can_change_user_role(client, auth_headers):
    """Admin should be able to change user roles."""
    # Create a regular user
    create_resp = client.post(
        "/api/v1/users",
        json={"username": "roletest", "email": "roletest@example.com", "password": "password123"},
    )
    assert create_resp.status_code == 201, create_resp.text
    user_id = create_resp.json()["id"]

    # Admin changes the user's role
    response = client.put(
        f"/api/v1/users/{user_id}",
        json={"role": "admin"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "admin"
