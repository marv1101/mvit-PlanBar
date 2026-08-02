"""Tests for role-based dependencies (require_admin_or_planer)."""

import pytest
from app.dependencies import require_admin_or_planer
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def dep_client(db_session):
    app = FastAPI()

    from app.dependencies import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    @app.get("/admin-or-planer")
    def admin_or_planer_endpoint(user=Depends(require_admin_or_planer)):
        return {"id": user.id, "role": user.role}

    return TestClient(app)


def test_require_admin_or_planer_admin(dep_client, db_session):
    from app.db.models.user import User

    user = User(
        username="dep_admin",
        email="dep_admin@example.com",
        password_hash="x",
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = _make_token(user.id)
    response = dep_client.get("/admin-or-planer", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_require_admin_or_planer_planer(dep_client, db_session):
    from app.db.models.user import User

    user = User(
        username="dep_planer",
        email="dep_planer@example.com",
        password_hash="x",
        role="planer",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = _make_token(user.id)
    response = dep_client.get("/admin-or-planer", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "planer"


def test_require_admin_or_planer_employee_forbidden(dep_client, db_session):
    from app.db.models.user import User

    user = User(
        username="dep_user",
        email="dep_user@example.com",
        password_hash="x",
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = _make_token(user.id)
    response = dep_client.get("/admin-or-planer", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def _make_token(user_id: int) -> str:
    from app.core.auth import create_access_token

    return create_access_token(str(user_id))
