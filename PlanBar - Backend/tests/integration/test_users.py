def test_login_invalid_password(client):
    response = client.post(
        "/api/v1/users/login",
        json={"email": "admin@test.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_register_login_and_refresh_token(client):
    new_user = {
        "username": "integrationtestuser",
        "email": "testuser@example.com",
        "password": "SecureP@ss1",
    }

    response = client.post("/api/v1/users", json=new_user)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == new_user["username"]
    assert data["email"] == new_user["email"]
    assert data["role"] == "user"

    login_response = client.post(
        "/api/v1/users/login",
        json={"email": new_user["email"], "password": new_user["password"]},
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert token_data["access_token"]
    assert token_data["refresh_token"]
    assert token_data["token_type"] == "bearer"

    auth_header = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_response = client.get("/api/v1/users/me", headers=auth_header)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == new_user["email"]

    refresh_response = client.post(
        "/api/v1/users/refresh-token",
        json={"refresh_token": token_data["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    assert refresh_data["access_token"]
    assert refresh_data["refresh_token"]


def test_invalid_token(client):
    auth_header = {"Authorization": "Bearer invalidtoken123"}
    response = client.get("/api/v1/users/me", headers=auth_header)
    assert response.status_code == 401


def test_refresh_token_invalid(client):
    response = client.post("/api/v1/users/refresh-token", json={"refresh_token": "invalid"})
    assert response.status_code == 422


def test_get_user_by_id(client, auth_headers):
    create_resp = client.post(
        "/api/v1/users",
        json={"username": "getuserbyid", "email": "getbyid@example.com", "password": "Password@123"},
    )
    user_id = create_resp.json()["id"]

    response = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "getbyid@example.com"


def test_get_user_not_found(client, auth_headers):
    response = client.get("/api/v1/users/99999", headers=auth_headers)
    assert response.status_code == 404


def test_update_user_by_id(client, auth_headers):
    create_resp = client.post(
        "/api/v1/users",
        json={"username": "updatable", "email": "updatable@example.com", "password": "Password@123"},
    )
    user_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/users/{user_id}",
        json={"username": "updatedname"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["username"] == "updatedname"


def test_update_user_not_found(client, auth_headers):
    response = client.put(
        "/api/v1/users/99999",
        json={"username": "nobody"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_user_by_id(client, auth_headers):
    create_resp = client.post(
        "/api/v1/users",
        json={"username": "deletable", "email": "deletable@example.com", "password": "Password@123"},
    )
    user_id = create_resp.json()["id"]

    response = client.delete(f"/api/v1/users/{user_id}", headers=auth_headers)
    assert response.status_code == 204


def test_delete_user_not_found(client, auth_headers):
    response = client.delete("/api/v1/users/99999", headers=auth_headers)
    assert response.status_code == 404


def test_change_password(client, auth_headers):
    register_resp = client.post(
        "/api/v1/users",
        json={"username": "changepwuser", "email": "changepw@example.com", "password": "oldPassword@123"},
    )
    register_resp.json()["id"]
    user_auth = {
        "Authorization": f"Bearer {client.post('/api/v1/users/login', json={'email': 'changepw@example.com', 'password': 'oldPassword@123'}).json()['access_token']}"
    }

    response = client.post(
        "/api/v1/users/change-password",
        json={"old_password": "oldPassword@123", "new_password": "newPassword@123"},
        headers=user_auth,
    )
    assert response.status_code == 200


def test_change_password_wrong_old(client, auth_headers):
    client.post(
        "/api/v1/users",
        json={"username": "changepwfail", "email": "changepwfail@example.com", "password": "oldPassword@123"},
    )
    user_auth = {
        "Authorization": f"Bearer {client.post('/api/v1/users/login', json={'email': 'changepwfail@example.com', 'password': 'oldPassword@123'}).json()['access_token']}"
    }

    response = client.post(
        "/api/v1/users/change-password",
        json={"old_password": "wrongpassword", "new_password": "newPassword@123"},
        headers=user_auth,
    )
    assert response.status_code == 401


def test_list_unlinked_employees(client, auth_headers):
    response = client.get("/api/v1/users/employees/unlinked", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
