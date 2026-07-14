"""Integration tests for DSGVO Art. 17 (Right to Erasure) and Art. 20 (Data Portability)."""

from app.db.models.employee import Employee
from app.db.models.pinboard import PinboardMessage, PinboardThread
from app.db.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Password that meets BSI complexity: upper, lower, digit, special
_VALID_PASSWORD = "Test@Pass123"


def _register_and_login(client, email: str, username: str) -> dict:
    """Register a user, log them in, and return auth headers."""
    reg_resp = client.post(
        "/api/v1/users",
        json={"username": username, "email": email, "password": _VALID_PASSWORD},
    )
    if reg_resp.status_code != 201:
        # User might already exist; try to login directly
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
            "first_name": "Max",
            "last_name": "Mustermann",
            "email": "max@example.com",
            "color": "#FF0000",
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
    db_session.expire_all()  # Force re-read from DB


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExportUserData:
    """DSGVO Art. 20 — data portability."""

    def test_export_user_data(self, client, auth_headers, db_session):
        """Create a user with linked data, export, and verify completeness."""
        # Create an employee linked to this user
        emp = _create_employee_via_api(client, auth_headers)
        user_resp = client.get("/api/v1/users/me", headers=auth_headers)
        user_id = user_resp.json()["id"]

        # Link employee to user via DB
        _link_employee_to_user(client, db_session, user_id, emp["id"])

        # Create a pinboard thread and message
        thread_resp = client.post(
            "/api/v1/pinboard/threads",
            json={"title": "GDPR Export Thread"},
            headers=auth_headers,
        )
        thread_id = thread_resp.json()["id"]
        msg_resp = client.post(
            f"/api/v1/pinboard/threads/{thread_id}/messages",
            json={"content": "My personal export message"},
            headers=auth_headers,
        )
        msg_resp.json()["id"]

        # Export data
        resp = client.get("/api/v1/gdpr/export", headers=auth_headers)
        assert resp.status_code == 200

        data = resp.json()
        assert "export_date" in data
        assert "user" in data
        assert "employee" in data
        assert "pinboard" in data
        assert "audit_logs" in data

        # Verify user data
        assert data["user"]["id"] == user_id
        assert data["user"]["email"] == "admin@test.com"

        # Verify employee data is present
        assert data["employee"] is not None
        assert data["employee"]["first_name"] == "Max"
        assert data["employee"]["last_name"] == "Mustermann"

        # Verify employee sub-data
        assert isinstance(data["employee"]["contracts"], list)
        assert isinstance(data["employee"]["timecards"], list)
        assert isinstance(data["employee"]["shift_wishes"], list)
        assert isinstance(data["employee"]["shiftplans"], list)

        # Verify pinboard data - find our specific thread and message
        thread_titles = [t["title"] for t in data["pinboard"]["threads"]]
        assert "GDPR Export Thread" in thread_titles

        msg_contents = [m["content"] for m in data["pinboard"]["messages"]]
        assert "My personal export message" in msg_contents

        # Verify audit logs are present (at least the export access log)
        assert len(data["audit_logs"]) >= 1

    def test_export_requires_auth(self, client):
        """Unauthenticated export request should return 401."""
        resp = client.get("/api/v1/gdpr/export")
        assert resp.status_code == 401

    def test_export_csv_format(self, client, auth_headers, db_session):
        """CSV export should return proper CSV with all sections."""
        emp = _create_employee_via_api(client, auth_headers)
        user_resp = client.get("/api/v1/users/me", headers=auth_headers)
        user_id = user_resp.json()["id"]
        _link_employee_to_user(client, db_session, user_id, emp["id"])

        thread_resp = client.post(
            "/api/v1/pinboard/threads",
            json={"title": "CSV Export Thread"},
            headers=auth_headers,
        )
        client.post(
            f"/api/v1/pinboard/threads/{thread_resp.json()['id']}/messages",
            json={"content": "CSV export message"},
            headers=auth_headers,
        )

        resp = client.get("/api/v1/gdpr/export?format=csv", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "text/csv; charset=utf-8"
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert "gdpr_export" in resp.headers.get("content-disposition", "")

        text = resp.text
        assert "# EXPORT_DATE" in text
        assert "# USER" in text
        assert "# EMPLOYEE" in text
        assert "# CONTRACTS" in text
        assert "# TIMECARDS" in text
        assert "# SHIFT_WISHES" in text
        assert "# SHIFTPLANS" in text
        assert "# PINBOARD_THREADS" in text
        assert "# PINBOARD_MESSAGES" in text
        assert "# AUDIT_LOGS" in text
        assert "admin@test.com" in text
        assert "Max" in text
        assert "CSV Export Thread" in text

    def test_export_content_disposition(self, client, auth_headers):
        """JSON export should include Content-Disposition header with attachment."""
        resp = client.get("/api/v1/gdpr/export", headers=auth_headers)
        assert resp.status_code == 200
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert "filename=" in resp.headers.get("content-disposition", "")
        assert ".json" in resp.headers.get("content-disposition", "")

    def test_export_invalid_format(self, client, auth_headers):
        """Invalid format parameter should return 422."""
        resp = client.get("/api/v1/gdpr/export?format=xml", headers=auth_headers)
        assert resp.status_code == 422


class TestAdminExportUserData:
    """DSGVO Art. 20 — admin data portability."""

    def test_admin_export_employee_json(self, client, auth_headers, db_session):
        """Admin can export a specific employee's data as JSON."""
        emp = _create_employee_via_api(client, auth_headers)
        user_resp = client.get("/api/v1/users/me", headers=auth_headers)
        user_id = user_resp.json()["id"]
        _link_employee_to_user(client, db_session, user_id, emp["id"])

        resp = client.get(
            f"/api/v1/admin/employees/{emp['id']}/export?format=json",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "application/json"
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert ".json" in resp.headers.get("content-disposition", "")

        data = resp.json()
        assert data["user"]["id"] == user_id
        assert data["employee"] is not None
        assert data["employee"]["first_name"] == "Max"

    def test_admin_export_employee_csv(self, client, auth_headers, db_session):
        """Admin can export a specific employee's data as CSV."""
        emp = _create_employee_via_api(client, auth_headers)
        user_resp = client.get("/api/v1/users/me", headers=auth_headers)
        user_id = user_resp.json()["id"]
        _link_employee_to_user(client, db_session, user_id, emp["id"])

        resp = client.get(
            f"/api/v1/admin/employees/{emp['id']}/export?format=csv",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "text/csv; charset=utf-8"
        assert "attachment" in resp.headers.get("content-disposition", "")

        assert "# USER" in resp.text
        assert "# EMPLOYEE" in resp.text
        assert "Max" in resp.text

    def test_admin_export_requires_auth(self, client, db_session):
        """Unauthenticated admin export should return 401."""
        resp = client.get("/api/v1/admin/employees/1/export")
        assert resp.status_code == 401

    def test_admin_export_requires_admin_role(self, client, employee_auth_headers):
        """Non-admin user cannot use admin export endpoint."""
        headers, emp_id = employee_auth_headers
        resp = client.get(
            f"/api/v1/admin/employees/{emp_id}/export",
            headers=headers,
        )
        assert resp.status_code == 403

    def test_admin_export_employee_not_found(self, client, auth_headers):
        """Exporting a non-existent employee returns 404."""
        resp = client.get(
            "/api/v1/admin/employees/99999/export",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_admin_export_invalid_format(self, client, auth_headers, db_session):
        """Invalid format on admin endpoint returns 422."""
        emp = _create_employee_via_api(client, auth_headers)
        resp = client.get(
            f"/api/v1/admin/employees/{emp['id']}/export?format=xml",
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestDeleteUserData:
    """DSGVO Art. 17 — right to erasure."""

    def test_delete_user_data(self, client, auth_headers, db_session):
        """Create a user with data, delete, verify anonymization."""
        # Create employee
        emp = _create_employee_via_api(client, auth_headers)
        user_resp = client.get("/api/v1/users/me", headers=auth_headers)
        user_id = user_resp.json()["id"]
        user_email = user_resp.json()["email"]

        # Link employee to user
        _link_employee_to_user(client, db_session, user_id, emp["id"])

        # Create pinboard data
        thread_resp = client.post(
            "/api/v1/pinboard/threads",
            json={"title": "Thread to be deleted"},
            headers=auth_headers,
        )
        thread_id = thread_resp.json()["id"]
        msg_resp = client.post(
            f"/api/v1/pinboard/threads/{thread_id}/messages",
            json={"content": "Sensitive message content"},
            headers=auth_headers,
        )
        msg_id = msg_resp.json()["id"]

        # Delete account
        resp = client.delete("/api/v1/gdpr/account", headers=auth_headers)
        assert resp.status_code == 200, f"Delete failed: {resp.status_code} {resp.text}"
        body = resp.json()
        assert "message" in body
        assert "details" in body
        assert "DSGVO" in body["message"]

        # Force expire session cache to see committed changes
        db_session.expire_all()

        # Verify user is deleted from database
        user = db_session.query(User).filter(User.id == user_id).first()
        assert user is None, "User should be deleted"

        # Verify employee is anonymized (not deleted)
        employee = db_session.query(Employee).filter(Employee.id == emp["id"]).first()
        assert employee is not None, "Employee should still exist (anonymized)"
        assert employee.first_name == "Gelöschter"
        assert employee.email != user_email
        assert employee.user_id is None

        # Verify pinboard message is anonymized
        message = db_session.query(PinboardMessage).filter(PinboardMessage.id == msg_id).first()
        assert message is not None
        assert message.content == "[Gelöscht gemäß DSGVO Art. 17]"

        # Verify pinboard thread author is unlinked
        thread = db_session.query(PinboardThread).filter(PinboardThread.id == thread_id).first()
        assert thread is not None
        assert thread.author_id == 0

    def test_delete_other_users_data_isolation(self, client, auth_headers, db_session):
        """Deleting one user's account does not affect another user."""
        # Get the first user's info
        user1_resp = client.get("/api/v1/users/me", headers=auth_headers)
        user1_id = user1_resp.json()["id"]
        user1_email = user1_resp.json()["email"]

        # Create second user with data
        headers2 = _register_and_login(client, "user2isolated@example.com", "user2isol")
        user2_resp = client.get("/api/v1/users/me", headers=headers2)
        user2_id = user2_resp.json()["id"]

        # Second user deletes their own account
        resp2 = client.delete("/api/v1/gdpr/account", headers=headers2)
        assert resp2.status_code == 200

        # Force expire cache
        db_session.expire_all()

        # Verify first user still exists in DB
        user1 = db_session.query(User).filter(User.id == user1_id).first()
        assert user1 is not None
        assert user1.email == user1_email

        # Verify second user was anonymized/deleted
        user2 = db_session.query(User).filter(User.id == user2_id).first()
        assert user2 is None

    def test_delete_requires_auth(self, client):
        """Unauthenticated deletion request should return 401."""
        resp = client.delete("/api/v1/gdpr/account")
        assert resp.status_code == 401

    def test_export_after_delete_fails(self, client):
        """After deleting an account, export should fail (user no longer exists)."""
        headers = _register_and_login(client, "gdprdeltest@example.com", "gdprdeltest")
        client.delete("/api/v1/gdpr/account", headers=headers)

        # The token is still valid but the user is deleted from DB
        resp = client.get("/api/v1/gdpr/export", headers=headers)
        # Should return 401 or 404 since user is deleted
        assert resp.status_code in (401, 404)
