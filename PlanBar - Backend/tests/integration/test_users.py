def test_register_login_and_refresh_token(client):
    new_user = {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "securepassword",
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
