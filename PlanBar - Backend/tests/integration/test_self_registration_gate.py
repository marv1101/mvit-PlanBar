"""Tests for Issue #163 — Self-Registration Gate.

The ``POST /api/v1/users`` endpoint must reject public sign-ups when
``settings.enable_self_registration`` is ``False`` (the production default).
Admins can still create users via the protected ``POST /api/v1/users/admin-create``
endpoint.
"""

from app.config import settings


def test_register_user_rejected_when_disabled(client):
    """Default: self-registration is OFF → 403 Forbidden."""
    original = settings.enable_self_registration
    settings.enable_self_registration = False
    try:
        response = client.post(
            "/api/v1/users",
            json={
                "username": "shouldbeBlock",
                "email": "blocked@example.com",
                "password": "SecureP@ss1",
            },
        )
        assert response.status_code == 403
        body = response.json()
        # Make sure the error message is informative and does not leak internals
        detail = body.get("detail", "")
        assert "registration" in detail.lower() or "disabled" in detail.lower()
    finally:
        settings.enable_self_registration = original


def test_register_user_allowed_when_enabled(client):
    """When the flag is explicitly on, registration succeeds (201)."""
    original = settings.enable_self_registration
    settings.enable_self_registration = True
    try:
        response = client.post(
            "/api/v1/users",
            json={
                "username": "registrationEnabledUser",
                "email": "enabled@example.com",
                "password": "SecureP@ss1",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "enabled@example.com"
        assert data["role"] == "user"
    finally:
        settings.enable_self_registration = original


def test_register_user_404_db_state_not_leaked_when_disabled(client):
    """When disabled, the endpoint must not reveal whether the user already exists.

    Both "new" and "already-existing" payloads should return 403, not 201/409.
    This prevents user-enumeration via the registration endpoint.
    """
    original = settings.enable_self_registration
    settings.enable_self_registration = False
    try:
        # First request: would-be-new user
        r1 = client.post(
            "/api/v1/users",
            json={
                "username": "enumuser1",
                "email": "enum1@example.com",
                "password": "SecureP@ss1",
            },
        )
        # Second request: same payload (would normally be 409)
        r2 = client.post(
            "/api/v1/users",
            json={
                "username": "enumuser1",
                "email": "enum1@example.com",
                "password": "SecureP@ss1",
            },
        )
        assert r1.status_code == 403
        assert r2.status_code == 403
    finally:
        settings.enable_self_registration = original
