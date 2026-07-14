import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import ConflictException, NotFoundException
from app.db.base import Base
from app.db.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate
from app.services.role_service import (
    create_role,
    delete_role,
    list_roles,
    update_role,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


def test_list_roles_empty(db_session):
    roles = list_roles(db_session)
    assert roles == []


def test_list_roles_returns_ordered(db_session):
    db_session.add_all(
        [
            Role(name="zebra", color="#ff0000"),
            Role(name="alpha", color="#00ff00"),
        ]
    )
    db_session.commit()
    roles = list_roles(db_session)
    assert [r.name for r in roles] == ["alpha", "zebra"]


def test_create_role(db_session):
    data = RoleCreate(name="nurse", color="#ff0000")
    role = create_role(db_session, data)
    assert role.name == "nurse"
    assert role.color == "#ff0000"
    assert role.id is not None


def test_create_role_duplicate_raises(db_session):
    data = RoleCreate(name="doctor")
    create_role(db_session, data)
    with pytest.raises(ConflictException):
        create_role(db_session, data)


def test_update_role(db_session):
    role = create_role(db_session, RoleCreate(name="old_name"))
    updated = update_role(db_session, role.id, RoleUpdate(name="new_name"))
    assert updated.name == "new_name"


def test_update_role_not_found_raises(db_session):
    with pytest.raises(NotFoundException):
        update_role(db_session, 99999, RoleUpdate(name="x"))


def test_update_role_duplicate_name_raises(db_session):
    create_role(db_session, RoleCreate(name="first"))
    role2 = create_role(db_session, RoleCreate(name="second"))
    with pytest.raises(ConflictException):
        update_role(db_session, role2.id, RoleUpdate(name="first"))


def test_delete_role(db_session):
    role = create_role(db_session, RoleCreate(name="to_delete"))
    delete_role(db_session, role.id)
    assert list_roles(db_session) == []


def test_delete_role_not_found_raises(db_session):
    with pytest.raises(NotFoundException):
        delete_role(db_session, 99999)
