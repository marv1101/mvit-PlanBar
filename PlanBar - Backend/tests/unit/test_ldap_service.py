from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.base import Base
from app.db.models.user import User
from app.schemas.user import UserCreate
from app.services.user_service import create_user


class MockEntry:
    def __init__(self, dn, cn, mail, member_of=None):
        self.entry_dn = dn
        self.cn = cn
        self.mail = mail
        if member_of is not None:
            self.memberOf = member_of


class MockEntries(list):
    pass


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def reset_ldap_settings():
    saved = {
        "enabled": settings.ldap_enabled,
        "server": settings.ldap_server,
        "bind_dn": settings.ldap_bind_dn,
        "bind_password": settings.ldap_bind_password,
        "user_search_base": settings.ldap_user_search_base,
        "user_search_filter": settings.ldap_user_search_filter,
        "role_mapping": settings.ldap_role_mapping.copy(),
        "use_tls": settings.ldap_use_tls,
    }
    yield
    settings.ldap_enabled = saved["enabled"]
    settings.ldap_server = saved["server"]
    settings.ldap_bind_dn = saved["bind_dn"]
    settings.ldap_bind_password = saved["bind_password"]
    settings.ldap_user_search_base = saved["user_search_base"]
    settings.ldap_user_search_filter = saved["user_search_filter"]
    settings.ldap_role_mapping = saved["role_mapping"]
    settings.ldap_use_tls = saved["use_tls"]


def enable_ldap():
    settings.ldap_enabled = True
    settings.ldap_server = "ldap://localhost:389"
    settings.ldap_bind_dn = "cn=admin,dc=example,dc=com"
    settings.ldap_bind_password = "secret"
    settings.ldap_user_search_base = "ou=users,dc=example,dc=com"
    settings.ldap_user_search_filter = "(objectClass=person)"


# --- ldap_test_connection ---


@patch("app.services.ldap_service.Connection")
@patch("app.services.ldap_service.Server")
def test_ldap_test_connection_disabled(_mock_server, _mock_conn):
    from app.services.ldap_service import ldap_test_connection

    settings.ldap_enabled = False
    result = ldap_test_connection()
    assert result["success"] is False
    assert "disabled" in result["message"].lower()


@patch("app.services.ldap_service.Connection")
@patch("app.services.ldap_service.Server")
def test_ldap_test_connection_success(mock_server, mock_conn):
    from app.services.ldap_service import ldap_test_connection

    enable_ldap()
    mock_server.return_value = MagicMock()
    mock_server.return_value.info = "OpenLDAP 2.4"
    mock_conn.return_value = MagicMock()

    result = ldap_test_connection()
    assert result["success"] is True
    assert "successful" in result["message"].lower()


@patch("app.services.ldap_service.Connection", side_effect=Exception("Connection refused"))
@patch("app.services.ldap_service.Server")
def test_ldap_test_connection_failure(mock_server, mock_conn):
    from app.services.ldap_service import ldap_test_connection

    enable_ldap()

    result = ldap_test_connection()
    assert result["success"] is False
    assert "Connection refused" in result["message"]


# --- ldap_authenticate ---


@patch("app.services.ldap_service.Connection")
@patch("app.services.ldap_service.Server")
def test_ldap_authenticate_disabled(_mock_server, _mock_conn, db_session):
    from app.services.ldap_service import ldap_authenticate

    settings.ldap_enabled = False
    result = ldap_authenticate(db_session, "user@test.com", "password")
    assert result is None


@patch("app.services.ldap_service.Connection")
@patch("app.services.ldap_service.Server")
def test_ldap_authenticate_no_connection(_mock_server, mock_conn, db_session):
    from app.services.ldap_service import ldap_authenticate

    enable_ldap()
    mock_conn.side_effect = Exception("LDAP unavailable")

    result = ldap_authenticate(db_session, "user@test.com", "password")
    assert result is None


@patch("app.services.ldap_service.Connection")
@patch("app.services.ldap_service.Server")
def test_ldap_authenticate_new_user(mock_server, mock_conn, db_session):
    from app.services.ldap_service import ldap_authenticate

    enable_ldap()

    mock_entry = MockEntry("cn=jdoe,ou=users,dc=example,dc=com", "jdoe", "jdoe@example.com", [])
    mock_entries = MockEntries([mock_entry])

    mock_conn_instance = MagicMock()
    mock_conn_instance.entries = mock_entries
    mock_conn.return_value = mock_conn_instance

    # Second Connection for user bind
    mock_user_conn = MagicMock()
    mock_conn.side_effect = [mock_conn_instance, mock_user_conn]

    result = ldap_authenticate(db_session, "jdoe@example.com", "password123")
    assert result is not None
    assert result.email == "jdoe@example.com"
    assert result.username == "jdoe"
    assert result.role == "user"

    user = db_session.query(User).filter(User.email == "jdoe@example.com").first()
    assert user is not None


@patch("app.services.ldap_service.Connection")
@patch("app.services.ldap_service.Server")
def test_ldap_authenticate_existing_user(mock_server, mock_conn, db_session):
    from app.services.ldap_service import ldap_authenticate

    enable_ldap()

    user = create_user(
        db_session,
        UserCreate(username="jdoe", email="jdoe@example.com", password="OldPass@123"),
    )
    assert user.role == "user"

    mock_entry = MockEntry("cn=jdoe,ou=users,dc=example,dc=com", "jdoe", "jdoe@example.com", [])
    mock_entries = MockEntries([mock_entry])

    mock_conn_instance = MagicMock()
    mock_conn_instance.entries = mock_entries
    mock_conn.side_effect = [mock_conn_instance, MagicMock()]

    result = ldap_authenticate(db_session, "jdoe@example.com", "password123")
    assert result is not None
    assert result.id == user.id
    assert result.role == "user"


@patch("app.services.ldap_service.Connection")
@patch("app.services.ldap_service.Server")
def test_ldap_authenticate_role_mapping(mock_server, mock_conn, db_session):
    from app.services.ldap_service import ldap_authenticate

    enable_ldap()
    settings.ldap_role_mapping = {"admins": "admin"}

    mock_entry = MockEntry(
        "cn=admin1,ou=users,dc=example,dc=com",
        "admin1",
        "admin1@example.com",
        ["CN=admins,OU=groups,DC=example,DC=com"],
    )
    mock_entries = MockEntries([mock_entry])

    mock_conn_instance = MagicMock()
    mock_conn_instance.entries = mock_entries
    mock_conn.side_effect = [mock_conn_instance, MagicMock()]

    result = ldap_authenticate(db_session, "admin1@example.com", "password123")
    assert result is not None
    assert result.role == "admin"


@patch("app.services.ldap_service.Connection")
@patch("app.services.ldap_service.Server")
def test_ldap_authenticate_user_not_found(mock_server, mock_conn, db_session):
    from app.services.ldap_service import ldap_authenticate

    enable_ldap()

    mock_entries = MockEntries([])

    mock_conn_instance = MagicMock()
    mock_conn_instance.entries = mock_entries
    mock_conn.return_value = mock_conn_instance

    result = ldap_authenticate(db_session, "unknown@example.com", "password123")
    assert result is None


# --- ldap_sync_all ---


@patch("app.services.ldap_service.Connection")
@patch("app.services.ldap_service.Server")
def test_ldap_sync_all_disabled(_mock_server, _mock_conn, db_session):
    from app.services.ldap_service import ldap_sync_all

    settings.ldap_enabled = False
    result = ldap_sync_all(db_session)
    assert result["users_created"] == 0
    assert result["users_updated"] == 0
    assert len(result["errors"]) == 1
    assert "disabled" in result["errors"][0].lower()


@patch("app.services.ldap_service.Connection")
@patch("app.services.ldap_service.Server")
def test_ldap_sync_all_success(mock_server, mock_conn, db_session):
    from app.services.ldap_service import ldap_sync_all

    enable_ldap()

    entries = [
        MockEntry("cn=jdoe,ou=users,dc=example,dc=com", "jdoe", "jdoe@example.com"),
        MockEntry("cn=asmith,ou=users,dc=example,dc=com", "asmith", "asmith@example.com"),
    ]
    mock_entries = MockEntries(entries)

    mock_conn_instance = MagicMock()
    mock_conn_instance.entries = mock_entries
    mock_conn.return_value = mock_conn_instance

    result = ldap_sync_all(db_session)
    assert result["users_created"] == 2
    assert result["users_updated"] == 0
    assert len(result["errors"]) == 0

    user1 = db_session.query(User).filter(User.email == "jdoe@example.com").first()
    assert user1 is not None
    assert user1.username == "jdoe"

    user2 = db_session.query(User).filter(User.email == "asmith@example.com").first()
    assert user2 is not None


# --- _map_ldap_role ---


def test_map_ldap_role_no_mapping():
    from app.services.ldap_service import _map_ldap_role

    settings.ldap_role_mapping = {}
    entry = MockEntry(
        "cn=test,dc=example,dc=com",
        "test", "test@example.com",
        ["CN=admins,OU=groups,DC=example,DC=com"],
    )
    assert _map_ldap_role(entry) == "user"


def test_map_ldap_role_with_mapping():
    from app.services.ldap_service import _map_ldap_role

    settings.ldap_role_mapping = {"admins": "admin"}
    entry = MockEntry(
        "cn=test,dc=example,dc=com",
        "test", "test@example.com",
        ["CN=admins,OU=groups,DC=example,DC=com"],
    )
    assert _map_ldap_role(entry) == "admin"


def test_map_ldap_role_no_member_of():
    from app.services.ldap_service import _map_ldap_role

    settings.ldap_role_mapping = {"admins": "admin"}
    entry = MockEntry("cn=test,dc=example,dc=com", "test", "test@example.com")
    assert _map_ldap_role(entry) == "user"
