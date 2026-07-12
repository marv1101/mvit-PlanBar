class TestRetentionEndpoints:
    def test_post_cleanup_as_admin_returns_report(self, client, db_session, auth_headers):
        response = client.post("/api/v1/retention/cleanup", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Retention cleanup completed"
        assert "report" in data
        assert "executed_by" in data
        assert data["executed_by"] == "testadmin"

    def test_post_cleanup_as_non_admin_forbidden(self, client, db_session):
        register_data = {
            "username": "regularuser",
            "email": "regular@test.com",
            "password": "TestPass@123",
        }
        client.post("/api/v1/users", json=register_data)
        login_response = client.post(
            "/api/v1/users/login",
            json={"email": "regular@test.com", "password": "TestPass@123"},
        )
        token = login_response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {token}"}

        response = client.post("/api/v1/retention/cleanup", headers=user_headers)
        assert response.status_code == 403

    def test_get_policies_lists_all_rules(self, client, db_session, auth_headers):
        response = client.get("/api/v1/retention/policies", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "policies" in data
        assert len(data["policies"]) >= 10
        for policy in data["policies"]:
            assert "key" in policy
            assert "description" in policy
            assert "retention_days" in policy
            assert "action" in policy
            assert "legal_basis" in policy

    def test_get_policies_as_non_admin_forbidden(self, client, db_session):
        register_data = {
            "username": "regularuser2",
            "email": "regular2@test.com",
            "password": "TestPass@123",
        }
        client.post("/api/v1/users", json=register_data)
        login_response = client.post(
            "/api/v1/users/login",
            json={"email": "regular2@test.com", "password": "TestPass@123"},
        )
        token = login_response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/retention/policies", headers=user_headers)
        assert response.status_code == 403

    def test_get_preview_shows_would_delete(self, client, db_session, auth_headers):
        response = client.get("/api/v1/retention/preview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Dry-run preview (no changes made)"
        assert "report" in data

    def test_get_preview_as_non_admin_forbidden(self, client, db_session):
        register_data = {
            "username": "regularuser3",
            "email": "regular3@test.com",
            "password": "TestPass@123",
        }
        client.post("/api/v1/users", json=register_data)
        login_response = client.post(
            "/api/v1/users/login",
            json={"email": "regular3@test.com", "password": "TestPass@123"},
        )
        token = login_response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/retention/preview", headers=user_headers)
        assert response.status_code == 403
