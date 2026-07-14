import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.auth import verify_password
from app.db.base import Base
from app.db.models.employee import Employee
from app.schemas.user import AdminUserCreate, UserCreate, UserUpdate
from app.services.user_service import (
    admin_create_user,
    authenticate_user,
    change_password,
    create_user,
    delete_user,
    get_user_by_id,
    list_users,
    update_user,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


def test_create_user(db_session):
    user_in = UserCreate(username="testuser", email="test@example.com", password="Secret@123")
    user = create_user(db_session, user_in)
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.role == "user"
    assert user.must_change_password is True


def test_create_user_admin_role(db_session):
    user_in = UserCreate(username="admin01", email="admin@example.com", password="Secret@123")
    user = create_user(db_session, user_in, role="admin")
    assert user.role == "admin"


def test_authenticate_user_success(db_session):
    user_in = UserCreate(username="authuser", email="auth@example.com", password="Correct@Pw1")
    create_user(db_session, user_in)
    user = authenticate_user(db_session, "auth@example.com", "Correct@Pw1")
    assert user is not None
    assert user.email == "auth@example.com"


def test_authenticate_user_wrong_email(db_session):
    user_in = UserCreate(username="authuser2", email="auth2@example.com", password="Correct@Pw1")
    create_user(db_session, user_in)
    user = authenticate_user(db_session, "nonexistent@example.com", "Correct@Pw1")
    assert user is None


def test_authenticate_user_wrong_password(db_session):
    user_in = UserCreate(username="authuser3", email="auth3@example.com", password="Correct@Pw1")
    create_user(db_session, user_in)
    user = authenticate_user(db_session, "auth3@example.com", "wrongpw")
    assert user is None


def test_get_user_by_id_found(db_session):
    user_in = UserCreate(username="getuser", email="get@example.com", password="Password@123")
    created = create_user(db_session, user_in)
    user = get_user_by_id(db_session, created.id)
    assert user is not None
    assert user.id == created.id


def test_get_user_by_id_not_found(db_session):
    user = get_user_by_id(db_session, 99999)
    assert user is None


def test_list_users(db_session):
    create_user(db_session, UserCreate(username="usr01", email="u1@example.com", password="Password@123"))
    create_user(db_session, UserCreate(username="usr02", email="u2@example.com", password="Password@123"))
    users = list_users(db_session)
    assert len(users) >= 2


def test_update_user_all_fields(db_session):
    created = create_user(db_session, UserCreate(username="oldname", email="old@example.com", password="OldPass@123"))
    updated = update_user(
        db_session,
        created,
        UserUpdate(username="newname", email="new@example.com", password="NewPass@123", role="admin"),
    )
    assert updated.username == "newname"
    assert updated.email == "new@example.com"
    assert updated.role == "admin"


def test_update_user_partial(db_session):
    created = create_user(
        db_session, UserCreate(username="partial", email="partial@example.com", password="Password@123")
    )
    updated = update_user(db_session, created, UserUpdate(username="onlyname"))
    assert updated.username == "onlyname"
    assert updated.email == "partial@example.com"


def test_delete_user(db_session):
    created = create_user(
        db_session, UserCreate(username="deleteme", email="delete@example.com", password="Password@123")
    )
    user_id = created.id
    delete_user(db_session, created)
    assert get_user_by_id(db_session, user_id) is None


def test_change_password_success(db_session):
    created = create_user(db_session, UserCreate(username="changepw", email="cpw@example.com", password="OldPass@123"))
    user = change_password(db_session, created, "OldPass@123", "NewPass@123")
    assert user.must_change_password is False
    assert verify_password("NewPass@123", user.password_hash) is True


def test_change_password_wrong_old_password(db_session):
    created = create_user(
        db_session, UserCreate(username="changepw2", email="cpw2@example.com", password="OldPass@123")
    )
    with pytest.raises(ValueError, match="Old password is incorrect"):
        change_password(db_session, created, "wrongpw", "NewPass@123")


def test_admin_create_user(db_session):
    admin_in = AdminUserCreate(username="admincreated", email="admcreated@example.com", role="admin")
    user, password = admin_create_user(db_session, admin_in)
    assert user.username == "admincreated"
    assert user.role == "admin"
    assert len(password) > 0


def test_admin_create_user_with_employee(db_session):
    employee = Employee(first_name="Test", last_name="User", email="emp@example.com")
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)

    admin_in = AdminUserCreate(
        username="adminwithemp",
        email="adminwithemp@example.com",
        role="admin",
        employee_id=employee.id,
    )
    user, password = admin_create_user(db_session, admin_in)
    db_session.refresh(employee)
    assert employee.user_id == user.id
