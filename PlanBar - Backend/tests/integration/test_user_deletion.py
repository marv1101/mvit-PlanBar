"""
GDPR Right to Deletion (Issue #40) - Integration Tests

TDD: These tests MUST fail before implementation.
"""

from datetime import datetime, timezone

from app.db.models.user import User


def test_soft_delete_user_sets_is_deleted_and_deleted_at(client, auth_headers, db_session):
    """When a user is deleted, is_deleted=True and deleted_at is set (not hard-deleted)."""
    # Create a user to delete
    create_resp = client.post(
        "/api/v1/users",
        json={
            "username": "gdpr_delete_me",
            "email": "gdpr_delete_me@example.com",
            "password": "password123",
        },
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    # Delete the user via admin endpoint
    response = client.delete(f"/api/v1/users/{user_id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify soft-delete: user still exists in DB but marked as deleted
    user = db_session.query(User).filter(User.id == user_id).first()
    assert user is not None, "User should still exist in DB (soft-delete)"
    assert user.is_deleted is True
    assert user.deleted_at is not None
    assert isinstance(user.deleted_at, datetime)


def test_soft_delete_cascades_to_employee_data(client, auth_headers, db_session):
    """When a user with linked Employee is deleted, personal data is pseudonymized."""
    from app.db.models.employee import Contract, Employee, Timecard
    from app.db.models.shift_wish import ShiftWish

    # Create a user
    create_resp = client.post(
        "/api/v1/users",
        json={
            "username": "gdpr_cascade_user",
            "email": "gdpr_cascade@example.com",
            "password": "password123",
        },
    )
    user_id = create_resp.json()["id"]
    user = db_session.query(User).filter(User.id == user_id).first()

    # Create a linked Employee with personal data
    employee = Employee(
        user_id=user.id,
        first_name="Sensitive",
        last_name="PersonalData",
        email="sensitive@example.com",
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)

    # Create related records
    contract = Contract(employee_id=employee.id, weekly_working_hours=40.0, break_time=30)
    db_session.add(contract)
    timecard = Timecard(employee_id=employee.id, week=1, year=2026, balance=8.0)
    db_session.add(timecard)
    shift_wish = ShiftWish(employee_id=employee.id, date=datetime(2026, 1, 5).date(), type="preferred")
    db_session.add(shift_wish)
    db_session.commit()

    # Delete the user
    response = client.delete(f"/api/v1/users/{user_id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify employee personal data is pseudonymized
    employee = db_session.query(Employee).filter(Employee.id == employee.id).first()
    assert employee is not None, "Employee record should still exist"
    assert employee.first_name != "Sensitive", "first_name should be pseudonymized"
    assert employee.last_name != "PersonalData", "last_name should be pseudonymized"
    assert employee.email != "sensitive@example.com", "email should be pseudonymized"

    # Records should still exist (not hard-deleted) for retention
    contract = db_session.query(Contract).filter(Contract.id == contract.id).first()
    assert contract is not None, "Contract should still exist for retention"
    timecard = db_session.query(Timecard).filter(Timecard.id == timecard.id).first()
    assert timecard is not None, "Timecard should still exist for retention"


def test_self_service_delete_endpoint(client, db_session):
    """Users can delete themselves via DELETE /api/v1/users/me."""
    # Register a user
    register_data = {
        "username": "self_delete_user",
        "email": "self_delete@example.com",
        "password": "password123",
    }
    create_resp = client.post("/api/v1/users", json=register_data)
    assert create_resp.status_code == 201

    # Login to get auth token
    login_resp = client.post(
        "/api/v1/users/login",
        json={"email": "self_delete@example.com", "password": "password123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Self-delete
    response = client.delete("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 204

    # Verify the user is soft-deleted
    user = db_session.query(User).filter(User.email == "self_delete@example.com").first()
    assert user is not None, "User should still exist in DB (soft-delete)"
    assert user.is_deleted is True
    assert user.deleted_at is not None


def test_cannot_delete_other_users_via_self_service(client, db_session):
    """The /me endpoint only deletes the authenticated user, not arbitrary users."""
    from app.db.models.employee import Employee

    # Create two users
    client.post(
        "/api/v1/users",
        json={
            "username": "user_a",
            "email": "user_a@example.com",
            "password": "password123",
        },
    )
    resp_b = client.post(
        "/api/v1/users",
        json={
            "username": "user_b",
            "email": "user_b@example.com",
            "password": "password123",
        },
    )
    user_b_id = resp_b.json()["id"]

    # Login as user_a
    login_resp = client.post(
        "/api/v1/users/login",
        json={"email": "user_a@example.com", "password": "password123"},
    )
    token = login_resp.json()["access_token"]
    auth_headers_a = {"Authorization": f"Bearer {token}"}

    # Try to delete user_b via /me (should only affect user_a)
    # The /me endpoint doesn't accept user_id - it uses the authenticated user
    response = client.delete("/api/v1/users/me", headers=auth_headers_a)
    assert response.status_code == 204

    # user_b should NOT be deleted
    user_b = db_session.query(User).filter(User.id == user_b_id).first()
    assert user_b is not None
    assert user_b.is_deleted is False, "user_b should not be affected by user_a's self-delete"

    # user_a should be soft-deleted
    user_a = db_session.query(User).filter(User.email == "user_a@example.com").first()
    assert user_a.is_deleted is True


def test_deletion_creates_audit_log(client, auth_headers, db_session):
    """Deletion should create an audit log entry recording who was deleted and when."""
    from app.db.models.audit import DeletionAuditLog

    # Create a user
    create_resp = client.post(
        "/api/v1/users",
        json={
            "username": "audit_test_user",
            "email": "audit_test@example.com",
            "password": "password123",
        },
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    # Get a timestamp before deletion
    before_deletion = datetime.now(timezone.utc)

    # Delete the user
    response = client.delete(f"/api/v1/users/{user_id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify audit log was created
    audit_logs = db_session.query(DeletionAuditLog).filter(
        DeletionAuditLog.deleted_user_id == user_id
    ).all()
    assert len(audit_logs) == 1, f"Expected 1 audit log entry, got {len(audit_logs)}"

    log = audit_logs[0]
    assert log.deleted_user_id == user_id
    assert log.deleted_at is not None
    # Note: SQLite stores naive datetimes; the audit log timestamp should be recent
    log_naive = log.deleted_at.replace(tzinfo=None)
    before_naive = before_deletion.replace(tzinfo=None)
    assert log_naive >= before_naive
    # Audit log should NOT contain personal data
    assert not hasattr(log, "email") or log.email is None
    assert not hasattr(log, "username") or log.username is None


def test_deleted_user_cannot_login(client, db_session):
    """A soft-deleted user should not be able to log in."""
    # Create and login a user
    client.post(
        "/api/v1/users",
        json={
            "username": "deleted_login_user",
            "email": "deleted_login@example.com",
            "password": "password123",
        },
    )

    # Login before deletion
    login_resp = client.post(
        "/api/v1/users/login",
        json={"email": "deleted_login@example.com", "password": "password123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Self-delete
    delete_resp = client.delete("/api/v1/users/me", headers=auth_headers)
    assert delete_resp.status_code == 204

    # Try to login again - should fail
    login_resp2 = client.post(
        "/api/v1/users/login",
        json={"email": "deleted_login@example.com", "password": "password123"},
    )
    assert login_resp2.status_code == 401


def test_deleted_user_cannot_access_api(client, db_session):
    """A soft-deleted user's existing tokens should not grant access."""
    # Create and login a user
    client.post(
        "/api/v1/users",
        json={
            "username": "deleted_api_user",
            "email": "deleted_api@example.com",
            "password": "password123",
        },
    )
    login_resp = client.post(
        "/api/v1/users/login",
        json={"email": "deleted_api@example.com", "password": "password123"},
    )
    token = login_resp.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Verify they can access /me
    me_resp = client.get("/api/v1/users/me", headers=auth_headers)
    assert me_resp.status_code == 200

    # Self-delete
    client.delete("/api/v1/users/me", headers=auth_headers)

    # Try to access /me again with same token - should fail
    me_resp2 = client.get("/api/v1/users/me", headers=auth_headers)
    assert me_resp2.status_code == 401


def test_deleted_user_excluded_from_user_list(client, auth_headers, db_session):
    """Soft-deleted users should not appear in the user list."""
    # Create a user
    create_resp = client.post(
        "/api/v1/users",
        json={
            "username": "list_delete_user",
            "email": "list_delete@example.com",
            "password": "password123",
        },
    )
    user_id = create_resp.json()["id"]

    # Delete the user via admin
    client.delete(f"/api/v1/users/{user_id}")

    # List users
    response = client.get("/api/v1/users", headers=auth_headers)
    assert response.status_code == 200
    user_ids = [u["id"] for u in response.json()]
    assert user_id not in user_ids
