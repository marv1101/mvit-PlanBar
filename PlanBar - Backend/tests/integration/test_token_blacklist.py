"""Integration tests for JWT token revocation via API."""

import uuid


def _create_user(client, password="TestPass@123"):
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
    return email


def _login(client, email, password="TestPass@123"):
    return client.post(
        "/api/v1/users/login",
        json={"email": email, "password": password},
    )


class TestTokenBlacklist:
    def test_logout_revokes_token(self, client):
        email = _create_user(client)
        login_resp = _login(client, email)
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me_resp = client.get("/api/v1/users/me", headers=headers)
        assert me_resp.status_code == 200

        logout_resp = client.post("/api/v1/users/logout", headers=headers)
        assert logout_resp.status_code == 200

        me_resp = client.get("/api/v1/users/me", headers=headers)
        assert me_resp.status_code == 401

    def test_logout_without_token(self, client):
        response = client.post("/api/v1/users/logout")
        assert response.status_code == 200

    def test_refresh_revokes_old_refresh_token(self, client):
        email = _create_user(client)
        login_resp = _login(client, email)
        old_refresh_token = login_resp.json()["refresh_token"]

        refresh_resp = client.post(
            "/api/v1/users/refresh-token",
            json={"refresh_token": old_refresh_token},
        )
        assert refresh_resp.status_code == 200

        refresh_resp2 = client.post(
            "/api/v1/users/refresh-token",
            json={"refresh_token": old_refresh_token},
        )
        assert refresh_resp2.status_code == 401

    def test_revoked_refresh_token_returns_401(self, client):
        email = _create_user(client)
        login_resp = _login(client, email)
        refresh_token = login_resp.json()["refresh_token"]

        client.post(
            "/api/v1/users/refresh-token",
            json={"refresh_token": refresh_token},
        )

        resp = client.post(
            "/api/v1/users/refresh-token",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 401

    def test_two_sessions_one_logout(self, client):
        email = _create_user(client)
        login_resp = _login(client, email)
        token1 = login_resp.json()["access_token"]

        login_resp2 = _login(client, email)
        token2 = login_resp2.json()["access_token"]

        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}

        assert client.get("/api/v1/users/me", headers=headers1).status_code == 200
        assert client.get("/api/v1/users/me", headers=headers2).status_code == 200

        client.cookies.clear()
        client.post("/api/v1/users/logout", headers=headers1)

        assert client.get("/api/v1/users/me", headers=headers1).status_code == 401
        assert client.get("/api/v1/users/me", headers=headers2).status_code == 200
