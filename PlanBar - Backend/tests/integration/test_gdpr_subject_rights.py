"""Integration tests for DSGVO Betroffenenrechte (Art. 15, 18, 21, 22).

These tests cover the subject rights endpoints that were added as part
of the GDPR compliance implementation.
"""

from app.db.models.employee import Employee
from app.db.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_PASSWORD = "Test@Pass123"


def _register_and_login(client, email: str, username: str) -> dict:
    """Register a user, log them in, and return auth headers."""
    reg_resp = client.post(
        "/api/v1/users",
        json={"username": username, "email": email, "password": _VALID_PASSWORD},
    )
    if reg_resp.status_code != 201:
        pass
    login_resp = client.post(
        "/api/v1/users/login",
        json={"email": email, "password": _VALID_PASSWORD},
    )
    data = login_resp.json()
    assert "access_token" in data, f"Login failed: {login_resp.status_code} {data}"
    return {"Authorization": f"Bearer {data['access_token']}"}


def _create_employee_via_api(client, headers: dict) -> dict:
    """Create an employee via the admin API and return the response body."""
    resp = client.post(
        "/api/v1/employees",
        json={
            "first_name": "GDPR",
            "last_name": "Subject",
            "email": "gdpr.subject@example.com",
            "color": "#00FF00",
        },
        headers=headers,
    )
    assert resp.status_code == 201, f"Employee creation failed: {resp.status_code} {resp.text}"
    return resp.json()


def _link_employee_to_user(client, db_session, user_id: int, employee_id: int):
    """Link an employee to a user by updating both sides of the relationship."""
    emp = db_session.query(Employee).filter(Employee.id == employee_id).first()
    assert emp is not None, f"Employee {employee_id} not found in DB"
    emp.user_id = user_id
    db_session.add(emp)
    user = db_session.query(User).filter(User.id == user_id).first()
    assert user is not None, f"User {user_id} not found in DB"
    user.employee_id = employee_id
    db_session.add(user)
    db_session.commit()
    db_session.expire_all()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDataAccess:
    """DSGVO Art. 15 — right to access (data access)."""

    def test_data_access_returns_full_report(self, client, auth_headers, db_session):
        """Access endpoint returns all required fields per Art. 15."""
        emp = _create_employee_via_api(client, auth_headers)
        user_resp = client.get("/api/v1/users/me", headers=auth_headers)
        user_id = user_resp.json()["id"]
        _link_employee_to_user(client, db_session, user_id, emp["id"])

        resp = client.get("/api/v1/gdpr/access", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert "personal_data" in data
        assert "processing_purposes" in data
        assert "data_recipients" in data
        assert "retention_periods" in data
        assert "rights" in data

        assert data["personal_data"]["user"]["id"] == user_id
        assert data["personal_data"]["user"]["email"] == "admin@test.com"
        assert data["personal_data"]["employee"] is not None
        assert data["personal_data"]["employee"]["first_name"] == "GDPR"
        assert data["personal_data"]["employee"]["last_name"] == "Subject"

        assert len(data["processing_purposes"]) > 0
        assert len(data["data_recipients"]) > 0
        assert len(data["retention_periods"]) > 0
        assert len(data["rights"]) > 0

    def test_data_access_requires_auth(self, client):
        """Unauthenticated access request should return 401."""
        resp = client.get("/api/v1/gdpr/access")
        assert resp.status_code == 401


class TestRestrictProcessing:
    """DSGVO Art. 18 — right to restrict processing."""

    def test_restrict_processing_toggles_flag(self, client, auth_headers, db_session):
        """Restrict processing toggles the flag and returns correct status."""
        resp = client.post("/api/v1/gdpr/restrict-processing", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert data["restricted"] is True

        resp2 = client.post("/api/v1/gdpr/restrict-processing", headers=auth_headers)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["restricted"] is False

    def test_restrict_processing_updates_employee(self, client, auth_headers, db_session):
        """When user has linked employee, restrict processing syncs to employee."""
        emp = _create_employee_via_api(client, auth_headers)
        user_resp = client.get("/api/v1/users/me", headers=auth_headers)
        user_id = user_resp.json()["id"]
        _link_employee_to_user(client, db_session, user_id, emp["id"])

        client.post("/api/v1/gdpr/restrict-processing", headers=auth_headers)
        db_session.expire_all()

        employee = db_session.query(Employee).filter(Employee.id == emp["id"]).first()
        assert employee is not None
        assert employee.processing_restricted is True

    def test_restrict_processing_requires_auth(self, client):
        """Unauthenticated restrict request should return 401."""
        resp = client.post("/api/v1/gdpr/restrict-processing")
        assert resp.status_code == 401


class TestObjectToProcessing:
    """DSGVO Art. 21 — right to object."""

    def test_object_to_processing_sets_flag_and_date(self, client, auth_headers, db_session):
        """Objection sets objection_filed=True and records objection_date."""
        resp = client.post("/api/v1/gdpr/object", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["objection_filed"] is True
        assert data["objection_date"] is not None
        assert "DSGVO Art. 21" in data["message"]

        user_resp = client.get("/api/v1/users/me", headers=auth_headers)
        user = user_resp.json()
        assert user["objection_filed"] is True
        assert user["objection_date"] is not None

    def test_object_to_processing_requires_auth(self, client):
        """Unauthenticated objection request should return 401."""
        resp = client.post("/api/v1/gdpr/object")
        assert resp.status_code == 401


class TestAutomatedDecisions:
    """DSGVO Art. 22 — automated individual decision-making."""

    def test_automated_decisions_returns_info(self, client, auth_headers):
        """Automated decisions endpoint returns structured info."""
        resp = client.get("/api/v1/gdpr/automated-decisions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "automated_decisions_used" in data
        assert "details" in data
        assert "right_to_review" in data
        assert data["automated_decisions_used"] is False

    def test_automated_decisions_requires_auth(self, client):
        """Unauthenticated automated-decisions request should return 401."""
        resp = client.get("/api/v1/gdpr/automated-decisions")
        assert resp.status_code == 401


class TestAdminRestrictProcessing:
    """DSGVO Art. 18 — admin restricts employee processing."""

    def test_admin_restrict_employee_toggles_flag(self, client, auth_headers, db_session):
        """Admin can toggle processing restriction for an employee."""
        emp = _create_employee_via_api(client, auth_headers)

        resp = client.post(
            f"/api/v1/admin/employees/{emp['id']}/restrict-processing",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["restricted"] is True

        resp2 = client.post(
            f"/api/v1/admin/employees/{emp['id']}/restrict-processing",
            headers=auth_headers,
        )
        assert resp2.status_code == 200
        assert resp2.json()["restricted"] is False

    def test_admin_restrict_employee_syncs_to_user(self, client, auth_headers, db_session):
        """Admin restrict employee also syncs to linked user."""
        emp = _create_employee_via_api(client, auth_headers)
        user_resp = client.get("/api/v1/users/me", headers=auth_headers)
        user_id = user_resp.json()["id"]
        _link_employee_to_user(client, db_session, user_id, emp["id"])

        client.post(
            f"/api/v1/admin/employees/{emp['id']}/restrict-processing",
            headers=auth_headers,
        )
        db_session.expire_all()

        user = db_session.query(User).filter(User.id == user_id).first()
        assert user is not None
        assert user.processing_restricted is True

    def test_admin_restrict_employee_not_found(self, client, auth_headers):
        """Restricting a non-existent employee returns 404."""
        resp = client.post(
            "/api/v1/admin/employees/99999/restrict-processing",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_admin_restrict_requires_auth(self, client):
        """Unauthenticated admin restrict request returns 401."""
        resp = client.post("/api/v1/admin/employees/1/restrict-processing")
        assert resp.status_code == 401

    def test_admin_restrict_requires_admin_role(self, client, employee_auth_headers):
        """Non-admin user cannot use admin restrict endpoint."""
        headers, emp_id = employee_auth_headers
        resp = client.post(
            f"/api/v1/admin/employees/{emp_id}/restrict-processing",
            headers=headers,
        )
        assert resp.status_code == 403
