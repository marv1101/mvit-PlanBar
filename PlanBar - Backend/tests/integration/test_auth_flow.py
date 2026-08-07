"""Integration tests for full authentication flow."""

import uuid


def _create_user(client, password="TestPass@123"):
    email = f"{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/api/v1/users",
        json={
            "username": email.split("@", maxsplit=1)[0],
            "email": email,
            "password": password,
        },
    )
    assert resp.status_code == 201, resp.text
    return email


def _login(client, email, password="TestPass@123"):
    return client.post(
        "/api/v1/users/login",
        json={"email": email, "password": password},
    )


def test_login_success(client):
    email = _create_user(client)
    response = _login(client, email)
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"  # noqa: S105 - token type, not a password
    assert data["must_change_password"] is True


def test_login_wrong_password(client):
    email = _create_user(client)
    response = _login(client, email, password="wrongpassword")
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]


def test_login_nonexistent_user(client):
    response = _login(client, "nobody@example.com")
    assert response.status_code == 401


def test_access_protected_endpoint_with_token(client):
    email = _create_user(client)
    login_resp = _login(client, email)
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == email


def test_access_protected_endpoint_without_token(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_access_protected_endpoint_with_invalid_token(client):
    headers = {"Authorization": "Bearer invalidtoken123"}
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 401


def test_refresh_token(client):
    email = _create_user(client)
    login_resp = _login(client, email)
    refresh_token = login_resp.json()["refresh_token"]

    response = client.post(
        "/api/v1/users/refresh-token",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]


def test_refresh_token_invalid(client):
    response = client.post(
        "/api/v1/users/refresh-token",
        json={"refresh_token": "invalid"},
    )
    assert response.status_code == 422


def test_logout(client):
    email = _create_user(client)
    login_resp = _login(client, email)
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/v1/users/logout", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out"

    me_resp = client.get("/api/v1/users/me", headers=headers)
    assert me_resp.status_code == 401


def test_change_password_clears_must_change_flag(client, db_session):
    email = _create_user(client)
    login_resp = _login(client, email)
    assert login_resp.json()["must_change_password"] is True
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    change_resp = client.post(
        "/api/v1/users/change-password",
        json={"old_password": "TestPass@123", "new_password": "NewPass@456"},
        headers=headers,
    )
    assert change_resp.status_code == 200

    login_resp2 = _login(client, email, "NewPass@456")
    assert login_resp2.json()["must_change_password"] is False


def test_login_after_password_change(client, db_session):
    email = _create_user(client)
    login_resp = _login(client, email)
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/v1/users/change-password",
        json={"old_password": "TestPass@123", "new_password": "Changed@5678"},
        headers=headers,
    )

    response = _login(client, email, "Changed@5678")
    assert response.status_code == 200

    response = _login(client, email, "TestPass@123")
    assert response.status_code == 401
