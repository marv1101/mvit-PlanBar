from app.services import audit_service


def _create_audit_log(db_session, user_id=None):
    return audit_service.log(
        db_session,
        user_id=user_id,
        action="TEST_ACTION",
        resource_type="test_resource",
        resource_id="42",
        details="test details",
        ip_address="127.0.0.1",
        user_agent="test-agent",
    )


class TestAuditEndpoints:
    def test_list_audit_logs_as_admin(self, client, db_session, auth_headers):
        _create_audit_log(db_session)
        response = client.get("/api/v1/audit-logs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert len(data["items"]) >= 1

    def test_list_audit_logs_with_filters(self, client, db_session, auth_headers):
        _create_audit_log(db_session)
        response = client.get(
            "/api/v1/audit-logs?action=TEST_ACTION",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert all(item["action"] == "TEST_ACTION" for item in data["items"])

    def test_list_audit_logs_pagination(self, client, db_session, auth_headers):
        for _ in range(25):
            _create_audit_log(db_session)
        response = client.get("/api/v1/audit-logs?offset=0&limit=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] >= 25
        assert data["offset"] == 0
        assert data["limit"] == 10

    def test_get_audit_log_by_id(self, client, db_session, auth_headers):
        entry = _create_audit_log(db_session)
        response = client.get(f"/api/v1/audit-logs/{entry.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == entry.id
        assert data["action"] == "TEST_ACTION"

    def test_get_audit_log_not_found(self, client, auth_headers):
        response = client.get("/api/v1/audit-logs/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_suspicious_patterns(self, client, db_session, auth_headers):
        for _ in range(5):
            audit_service.log(
                db_session,
                user_id=None,
                action="LOGIN_FAILED",
                resource_type="user",
                resource_id="test@test.com",
                ip_address="10.0.0.1",
            )
        response = client.get("/api/v1/audit-logs/suspicious", headers=auth_headers)
        assert response.status_code == 200
        patterns = response.json()
        assert len(patterns) >= 1

    def test_export_audit_logs(self, client, db_session, auth_headers):
        _create_audit_log(db_session)
        response = client.get("/api/v1/audit-logs/export", headers=auth_headers)
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "filename=audit_logs.csv" in response.headers["content-disposition"]

    def test_list_non_admin_gets_forbidden(self, client, db_session):

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

        response = client.get("/api/v1/audit-logs", headers=user_headers)
        assert response.status_code == 403

    def test_get_single_non_admin_gets_forbidden(self, client, db_session):

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

        response = client.get("/api/v1/audit-logs/1", headers=user_headers)
        assert response.status_code == 403

    def test_suspicious_non_admin_gets_forbidden(self, client, db_session):

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

        response = client.get("/api/v1/audit-logs/suspicious", headers=user_headers)
        assert response.status_code == 403

    def test_export_non_admin_gets_forbidden(self, client, db_session):

        register_data = {
            "username": "regularuser4",
            "email": "regular4@test.com",
            "password": "TestPass@123",
        }
        client.post("/api/v1/users", json=register_data)
        login_response = client.post(
            "/api/v1/users/login",
            json={"email": "regular4@test.com", "password": "TestPass@123"},
        )
        token = login_response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/audit-logs/export", headers=user_headers)
        assert response.status_code == 403
