"""Integration tests for LDAP admin endpoints and login flow."""

from unittest.mock import MagicMock, patch

import pytest

from app.config import settings


class _MockEntry:
    def __init__(self, dn, cn, mail, member_of=None):
        self.entry_dn = dn
        self.cn = cn
        self.mail = mail
        if member_of is not None:
            self.memberOf = member_of


class _MockEntries(list):
    pass


@pytest.fixture(autouse=True)
def enable_ldap_settings():
    saved_enabled = settings.ldap_enabled
    settings.ldap_enabled = True
    yield
    settings.ldap_enabled = saved_enabled


@pytest.fixture(autouse=True)
def reset_role_mapping():
    saved = settings.ldap_role_mapping.copy()
    yield
    settings.ldap_role_mapping = saved


# --- LDAP Test Endpoint ---


@patch("app.services.ldap_service.ldap_test_connection")
def test_ldap_test_no_auth(mock_test, client):
    mock_test.return_value = {"success": True, "message": "ok"}
    response = client.post("/api/v1/ldap/test")
    assert response.status_code == 401


@patch("app.services.ldap_service.ldap_test_connection")
def test_ldap_test_non_admin(mock_test, client, employee_auth_headers):
    mock_test.return_value = {"success": True, "message": "ok"}
    headers, _ = employee_auth_headers
    response = client.post("/api/v1/ldap/test", headers=headers)
    assert response.status_code == 403


@patch("app.services.ldap_service.ldap_test_connection")
def test_ldap_test_success(mock_test, client, auth_headers):
    mock_test.return_value = {
        "success": True,
        "message": "LDAP connection successful",
        "server_info": "OpenLDAP 2.4",
    }
    response = client.post("/api/v1/ldap/test", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "successful" in data["message"]


@patch("app.services.ldap_service.ldap_test_connection")
def test_ldap_test_failure(mock_test, client, auth_headers):
    mock_test.return_value = {
        "success": False,
        "message": "LDAP connection failed: Connection refused",
        "server_info": None,
    }
    response = client.post("/api/v1/ldap/test", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "Connection refused" in data["message"]


# --- LDAP Sync Endpoint ---


@patch("app.services.ldap_service.ldap_sync_all")
def test_ldap_sync_no_auth(mock_sync, client):
    mock_sync.return_value = {"users_created": 0, "users_updated": 0, "errors": []}
    response = client.post("/api/v1/ldap/sync")
    assert response.status_code == 401


@patch("app.services.ldap_service.ldap_sync_all")
def test_ldap_sync_non_admin(mock_sync, client, employee_auth_headers):
    mock_sync.return_value = {"users_created": 0, "users_updated": 0, "errors": []}
    headers, _ = employee_auth_headers
    response = client.post("/api/v1/ldap/sync", headers=headers)
    assert response.status_code == 403


@patch("app.services.ldap_service.ldap_sync_all")
def test_ldap_sync_success(mock_sync, client, auth_headers):
    mock_sync.return_value = {"users_created": 3, "users_updated": 1, "errors": []}
    response = client.post("/api/v1/ldap/sync", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["users_created"] == 3
    assert data["users_updated"] == 1
    assert data["errors"] == []


@patch("app.services.ldap_service.ldap_sync_all")
def test_ldap_sync_with_errors(mock_sync, client, auth_headers):
    mock_sync.return_value = {
        "users_created": 1,
        "users_updated": 0,
        "errors": ["Error processing cn=bad,ou=users,dc=example,dc=com: Missing mail"],
    }
    response = client.post("/api/v1/ldap/sync", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["users_created"] == 1
    assert len(data["errors"]) == 1


# --- LDAP Status Endpoint ---


def test_ldap_status_no_auth(client):
    response = client.get("/api/v1/ldap/status")
    assert response.status_code == 401


def test_ldap_status_non_admin(client, employee_auth_headers):
    headers, _ = employee_auth_headers
    response = client.get("/api/v1/ldap/status", headers=headers)
    assert response.status_code == 403


def test_ldap_status_success(client, auth_headers):
    response = client.get("/api/v1/ldap/status", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "server" in data
    assert "user_search_base" in data
    assert "group_search_base" in data
    assert "use_tls" in data
    assert "last_sync" in data


# --- Login with LDAP (fallback test) ---


@patch("app.services.ldap_service.ldap_authenticate")
def test_login_ldap_authenticate_called(mock_ldap_auth, client, db_session):
    """LDAP authenticate should be called when LDAP is enabled."""
    mock_ldap_auth.return_value = None

    client.post(
        "/api/v1/users/login",
        json={"email": "nonexistent@test.com", "password": "SomePass@123"},
    )
    mock_ldap_auth.assert_called_once()


@patch("app.services.ldap_service.Server")
@patch("app.services.ldap_service.Connection")
def test_login_ldap_creates_user(mock_conn, mock_server, client, db_session):
    """Login via LDAP should create user if not exists."""
    settings.ldap_enabled = True
    settings.ldap_server = "ldap://localhost:389"
    settings.ldap_bind_dn = "cn=admin,dc=example,dc=com"
    settings.ldap_bind_password = "secret"
    settings.ldap_user_search_base = "ou=users,dc=example,dc=com"
    settings.ldap_user_search_filter = "(objectClass=person)"

    mock_entry = _MockEntry(
        "cn=jdoe,ou=users,dc=example,dc=com",
        "jdoe",
        "ldapuser@test.com",
        [],
    )
    mock_entries = _MockEntries([mock_entry])

    mock_conn_instance = MagicMock()
    mock_conn_instance.entries = mock_entries
    mock_conn.side_effect = [mock_conn_instance, MagicMock()]

    response = client.post(
        "/api/v1/users/login",
        json={"email": "ldapuser@test.com", "password": "ldappass123"},
    )
    assert response.status_code == 200

    from app.db.models.user import User

    user = db_session.query(User).filter(User.email == "ldapuser@test.com").first()
    assert user is not None
    assert user.username == "jdoe"
    assert user.role == "user"


@patch("app.services.ldap_service.Server")
@patch("app.services.ldap_service.Connection")
def test_login_ldap_fallback_to_local(mock_conn, mock_server, client, db_session):
    """When LDAP is enabled but fails, local auth should still work."""
    settings.ldap_enabled = True
    settings.ldap_server = "ldap://localhost:389"
    settings.ldap_bind_dn = "cn=admin,dc=example,dc=com"
    settings.ldap_bind_password = "secret"
    settings.ldap_user_search_base = "ou=users,dc=example,dc=com"

    mock_conn.side_effect = Exception("LDAP unavailable")

    client.post(
        "/api/v1/users",
        json={
            "username": "localuser",
            "email": "local@test.com",
            "password": "TestPass@123",
        },
    )

    response = client.post(
        "/api/v1/users/login",
        json={"email": "local@test.com", "password": "TestPass@123"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


# --- Role mapping via login ---


@patch("app.services.ldap_service.Server")
@patch("app.services.ldap_service.Connection")
def test_login_ldap_role_mapping(mock_conn, mock_server, client, db_session):
    """LDAP group should map to PlanBar admin role on login."""
    settings.ldap_enabled = True
    settings.ldap_server = "ldap://localhost:389"
    settings.ldap_bind_dn = "cn=admin,dc=example,dc=com"
    settings.ldap_bind_password = "secret"
    settings.ldap_user_search_base = "ou=users,dc=example,dc=com"
    settings.ldap_user_search_filter = "(objectClass=person)"
    settings.ldap_role_mapping = {"admins": "admin"}

    mock_entry = _MockEntry(
        "cn=admin1,ou=users,dc=example,dc=com",
        "admin1",
        "adminldap@test.com",
        ["CN=admins,OU=groups,DC=example,DC=com"],
    )
    mock_entries = _MockEntries([mock_entry])

    mock_conn_instance = MagicMock()
    mock_conn_instance.entries = mock_entries
    mock_conn.side_effect = [mock_conn_instance, MagicMock()]

    response = client.post(
        "/api/v1/users/login",
        json={"email": "adminldap@test.com", "password": "adminpass123"},
    )
    assert response.status_code == 200

    from app.db.models.user import User

    user = db_session.query(User).filter(User.email == "adminldap@test.com").first()
    assert user is not None
    assert user.role == "admin"
