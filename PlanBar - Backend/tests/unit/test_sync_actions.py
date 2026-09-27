"""Unit tests for SyncAction strategy pattern (Issue #148)."""

import uuid
from datetime import date as _date
from datetime import time as _time
from unittest.mock import Mock

import pytest
from app.db.models.employee import Employee
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User
from app.services.sync_actions import (
    CreateShiftWish,
    DeleteShiftWish,
    SyncActionRegistry,
    UpdateSchedule,
    UpdateShift,
    UpdateShiftWish,
)
from fastapi import HTTPException


def _u(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def admin_user(db_session):
    user = User(username=_u("admin"), email=f"{_u('admin')}@x.com", password_hash="x", role="admin")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def regular_user(db_session):
    user = User(username=_u("reg"), email=f"{_u('reg')}@x.com", password_hash="x", role="user")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def employee_user(db_session, regular_user):
    emp = Employee(first_name="T", last_name="E", email=f"{_u('emp')}@x.com", user_id=regular_user.id)
    db_session.add(emp)
    db_session.commit()
    regular_user.employee_id = emp.id
    db_session.commit()
    return regular_user


class TestCreateShiftWish:
    def test_create_shift_wish_success(self, db_session, employee_user):
        data = {
            "employee_id": employee_user.employee_id,
            "date": "2026-06-01",
            "week": 23,
            "type": "preferred",
            "note": "Test note",
        }
        result = CreateShiftWish.execute(db_session, data, employee_user)
        assert result["employee_id"] == employee_user.employee_id
        assert result["date"] == "2026-06-01"
        assert result["type"] == "preferred"
        assert result["note"] == "Test note"
        assert result["status"] == "pending"
        assert result["week"] == 1
        assert "id" in result
        w = db_session.query(ShiftWish).filter(ShiftWish.id == result["id"]).first()
        assert w is not None

    def test_create_shift_wish_with_default_values(self, db_session, employee_user):
        result = CreateShiftWish.execute(db_session, {"date": "2026-06-01"}, employee_user)
        assert result["type"] == "preferred"
        assert result["status"] == "pending"


class TestUpdateShiftWish:
    def test_update_shift_wish_success(self, db_session, employee_user, admin_user):
        c = CreateShiftWish.execute(
            db_session,
            {
                "employee_id": employee_user.employee_id,
                "date": "2026-06-01",
                "week": 23,
                "type": "preferred",
                "note": "Original",
            },
            employee_user,
        )
        r = UpdateShiftWish.execute(db_session, {"id": c["id"], "note": "Updated", "type": "unavailable"}, admin_user)
        assert r["id"] == c["id"]
        assert r["note"] == "Updated"
        assert r["type"] == "unavailable"

    def test_update_shift_wish_not_found(self, db_session, admin_user):
        with pytest.raises(HTTPException) as e:
            UpdateShiftWish.execute(db_session, {"id": 99999, "note": "x"}, admin_user)
        assert e.value.status_code == 404
        assert "Shift wish not found" in str(e.value)

    def test_update_shift_wish_derives_week_from_date(self, db_session, employee_user, admin_user):
        c = CreateShiftWish.execute(db_session, {"date": "2026-06-01", "type": "preferred"}, employee_user)
        r = UpdateShiftWish.execute(db_session, {"id": c["id"], "date": "2026-06-08"}, admin_user)
        assert r["date"] == "2026-06-08"
        assert r["week"] == 2


class TestDeleteShiftWish:
    def test_delete_shift_wish_success(self, db_session, employee_user):
        c = CreateShiftWish.execute(
            db_session,
            {
                "employee_id": employee_user.employee_id,
                "date": "2026-06-01",
                "week": 23,
                "type": "preferred",
                "note": "del",
            },
            employee_user,
        )
        r = DeleteShiftWish.execute(db_session, {"id": c["id"]}, employee_user)
        assert r["id"] == c["id"] and r["deleted"] is True
        assert db_session.query(ShiftWish).filter(ShiftWish.id == c["id"]).first() is None


class TestUpdateSchedule:
    def test_update_schedule_success(self, db_session, admin_user):
        s = Schedule(name="Orig", status="draft", week_type="A")
        db_session.add(s)
        db_session.commit()
        r = UpdateSchedule.execute(
            db_session, {"id": s.id, "name": "Test Schedule", "status": "draft", "week_type": "A"}, admin_user
        )
        assert r["id"] == s.id
        assert r["name"] == "Test Schedule"
        assert r["status"] == "draft"
        assert r["week_type"] == "A"


class TestUpdateShift:
    def test_update_shift_success(self, db_session, admin_user):
        sp = Shiftplan(
            schedule_id=1,
            employee_id=1,
            date=_date(2026, 6, 1),
            shift_id="morning",
            start_time=_time(8, 0),
            end_time=_time(16, 0),
        )
        db_session.add(sp)
        db_session.commit()
        r = UpdateShift.execute(
            db_session,
            {
                "id": sp.id,
                "employee_id": 1,
                "date": "2026-06-01",
                "shift_id": "morning",
                "start_time": "09:00",
                "end_time": "17:00",
                "week": "A",
                "break_start": "12:00",
                "break_end": "13:00",
                "label": "Workday",
                "notes": "Important tasks",
            },
            admin_user,
        )
        assert r["id"] == sp.id
        assert r["employee_id"] == 1
        assert r["date"] == "2026-06-01"
        assert r["shift_id"] == "morning"
        assert r["start_time"] == "09:00"
        assert r["end_time"] == "17:00"
        assert r["week"] == "A"
        assert r["break_start"] == "12:00"
        assert r["break_end"] == "13:00"
        assert r["label"] == "Workday"
        assert r["notes"] == "Important tasks"

    def test_update_shift_derives_week_on_date_change(self, db_session, admin_user):
        sp = Shiftplan(
            schedule_id=1,
            employee_id=2,
            date=_date(2026, 6, 2),
            shift_id="evening",
            start_time=_time(14, 0),
            end_time=_time(22, 0),
        )
        db_session.add(sp)
        db_session.commit()
        r = UpdateShift.execute(db_session, {"id": sp.id, "date": "2026-06-10"}, admin_user)
        assert r["date"] == "2026-06-10"
        assert r["week"] == "B"

    def test_update_shift_scope_rejects_other_parity(self, db_session, admin_user):
        s = Schedule(name="Scoped", status="draft", week_type="A")
        db_session.add(s)
        db_session.commit()
        sp = Shiftplan(
            schedule_id=s.id,
            employee_id=3,
            date=_date(2026, 6, 3),
            shift_id="night",
            start_time=_time(22, 0),
            end_time=_time(6, 0),
        )
        db_session.add(sp)
        db_session.commit()
        with pytest.raises(HTTPException) as e:
            UpdateShift.execute(db_session, {"id": sp.id, "date": "2026-06-10"}, admin_user)
        assert e.value.status_code == 422


class TestSyncActionRegistry:
    def test_register_and_get_action(self):
        m = Mock(spec=CreateShiftWish)
        m.resource = "requests"
        m.action = "create"
        m.role.check = Mock()
        m.execute = Mock(return_value={})
        SyncActionRegistry.register(m)
        assert SyncActionRegistry.get("requests", "create") is m
        m.role.check.assert_not_called()

    def test_get_nonexistent_action_raises_error(self):
        with pytest.raises(HTTPException) as e:
            SyncActionRegistry.get("nonexistent", "action")
        assert e.value.status_code == 400
        assert "Unsupported action" in str(e.value)

    def test_dispatch_calls_auth_and_execute(self, db_session, admin_user):
        m = Mock(spec=CreateShiftWish)
        m.resource = "requests"
        m.action = "create"
        m.role.check = Mock()
        m.execute = Mock(return_value={"id": 1})
        SyncActionRegistry.register(m)
        p = Mock()
        p.resource = "requests"
        p.action = "create"
        p.data = {"test": "data"}
        r = SyncActionRegistry.dispatch(p, db_session, admin_user)
        m.role.check.assert_called_once_with(admin_user)
        m.execute.assert_called_once_with(db_session, {"test": "data"}, admin_user)
        assert r == {"id": 1}
