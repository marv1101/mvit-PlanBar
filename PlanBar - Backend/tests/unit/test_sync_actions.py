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
    @staticmethod
    def _own_schedule(db_session, name="ShiftSched"):
        """Own week_type=None schedule (no parity restriction) instead of the
        hard-coded schedule_id=1, which is order-dependent in the shared test DB.
        """
        s = Schedule(name=_u(name), status="draft", week_type=None)
        db_session.add(s)
        db_session.commit()
        return s

    def test_update_shift_success(self, db_session, admin_user):
        s = self._own_schedule(db_session)
        sp = Shiftplan(
            schedule_id=s.id,
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
        s = self._own_schedule(db_session)
        sp = Shiftplan(
            schedule_id=s.id,
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
    def test_register_and_get_action(self, clean_registry):
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

    def test_dispatch_calls_auth_and_execute(self, db_session, admin_user, clean_registry):
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
        m.role.check.assert_called_once_with(admin_user, db_session, {"test": "data"})
        m.execute.assert_called_once_with(db_session, {"test": "data"}, admin_user)
        assert r == {"id": 1}


@pytest.fixture
def clean_registry():
    """Restore the real action registrations after a test mutated the registry."""
    yield
    SyncActionRegistry.reset()
    from app.services import sync_actions

    for action in (
        sync_actions.CreateShiftWish,
        sync_actions.UpdateShiftWish,
        sync_actions.DeleteShiftWish,
        sync_actions.UpdateSchedule,
        sync_actions.UpdateShift,
    ):
        SyncActionRegistry.register(action)


def _make_wish(db_session, employee_id, note="w"):
    wish = ShiftWish(employee_id=employee_id, date=_date(2026, 6, 1), week=23, type="preferred", note=note)
    db_session.add(wish)
    db_session.commit()
    return wish


def _make_planer(db_session):
    """Planer user (role=planer) with an employee linked to a new team.

    Returns (user, planer_employee, team).
    """
    from app.db.models.team import Team

    team = Team(name=_u("team"))
    db_session.add(team)
    db_session.commit()

    emp = Employee(first_name="P", last_name="L", email=f"{_u('planer')}@x.com")
    emp.teams.append(team)
    db_session.add(emp)
    db_session.commit()

    user = User(username=_u("pl"), email=f"{_u('pl')}@x.com", password_hash="x", role="planer", employee_id=emp.id)
    db_session.add(user)
    db_session.commit()
    return user, emp, team


def _team_member_with_wish(db_session, team, note="member-wish"):
    """Employee in *team* plus a wish owned by that employee."""
    emp = Employee(first_name="T", last_name="M", email=f"{_u('member')}@x.com")
    emp.teams.append(team)
    db_session.add(emp)
    db_session.commit()
    return emp, _make_wish(db_session, emp.id, note=note)


def _foreign_employee_user(db_session):
    """Role-'user' account linked to its OWN employee — distinct from the
    ``employee_user`` fixture (which doubles as ``regular_user``).
    """
    emp = Employee(first_name="F", last_name="U", email=f"{_u('foreignuser')}@x.com")
    db_session.add(emp)
    db_session.commit()
    user = User(username=_u("fu"), email=f"{_u('fu')}@x.com", password_hash="x", role="user", employee_id=emp.id)
    db_session.add(user)
    db_session.commit()
    return user, emp


class TestCreateShiftWishOwnership:
    def test_create_for_foreign_employee_denied(self, db_session, employee_user):
        foreign = Employee(first_name="F", last_name="X", email=f"{_u('foreign')}@x.com")
        db_session.add(foreign)
        db_session.commit()
        with pytest.raises(HTTPException) as e:
            CreateShiftWish.role.check(employee_user, db_session, {"employee_id": foreign.id})
        assert e.value.status_code == 403

    def test_create_for_own_employee_allowed(self, db_session, employee_user):
        CreateShiftWish.role.check(employee_user, db_session, {"employee_id": employee_user.employee_id})


class TestUpdateShiftWishRoleCheck:
    def test_owner_can_update_own_wish(self, db_session, employee_user):
        wish = _make_wish(db_session, employee_user.employee_id)
        UpdateShiftWish.role.check(employee_user, db_session, {"id": wish.id})

    def test_regular_user_cannot_update_foreign_wish(self, db_session, employee_user):
        foreign_user, _foreign_emp = _foreign_employee_user(db_session)
        wish = _make_wish(db_session, employee_user.employee_id)
        with pytest.raises(HTTPException) as e:
            UpdateShiftWish.role.check(foreign_user, db_session, {"id": wish.id})
        assert e.value.status_code == 403

    def test_team_planer_can_update_team_wish(self, db_session):
        planer, _planer_emp, team = _make_planer(db_session)
        member, wish = _team_member_with_wish(db_session, team)
        UpdateShiftWish.role.check(planer, db_session, {"id": wish.id})
        assert member.id

    def test_planer_cannot_update_foreign_wish(self, db_session, employee_user):
        planer, _planer_emp, _team = _make_planer(db_session)
        wish = _make_wish(db_session, employee_user.employee_id)
        with pytest.raises(HTTPException) as e:
            UpdateShiftWish.role.check(planer, db_session, {"id": wish.id})
        assert e.value.status_code == 403

    def test_user_cannot_change_status(self, db_session, employee_user):
        wish = _make_wish(db_session, employee_user.employee_id)
        with pytest.raises(HTTPException) as e:
            UpdateShiftWish.role.check(employee_user, db_session, {"id": wish.id, "status": "approved"})
        assert e.value.status_code == 403
        assert "Only admins or planners" in str(e.value)

    def test_planer_can_change_status(self, db_session):
        planer, _planer_emp, team = _make_planer(db_session)
        _member, wish = _team_member_with_wish(db_session, team)
        UpdateShiftWish.role.check(planer, db_session, {"id": wish.id, "status": "approved"})

    def test_owner_cannot_reassign_wish_to_foreign_employee(self, db_session, employee_user):
        foreign = Employee(first_name="F", last_name="Y", email=f"{_u('foreign')}@x.com")
        db_session.add(foreign)
        db_session.commit()
        wish = _make_wish(db_session, employee_user.employee_id)
        with pytest.raises(HTTPException) as e:
            UpdateShiftWish.role.check(employee_user, db_session, {"id": wish.id, "employee_id": foreign.id})
        assert e.value.status_code == 403


class TestDeleteShiftWishRoleCheck:
    def test_owner_can_delete_own_wish(self, db_session, employee_user):
        wish = _make_wish(db_session, employee_user.employee_id)
        DeleteShiftWish.role.check(employee_user, db_session, {"id": wish.id})

    def test_regular_user_cannot_delete_foreign_wish(self, db_session, employee_user):
        foreign_user, _foreign_emp = _foreign_employee_user(db_session)
        wish = _make_wish(db_session, employee_user.employee_id)
        with pytest.raises(HTTPException) as e:
            DeleteShiftWish.role.check(foreign_user, db_session, {"id": wish.id})
        assert e.value.status_code == 403

    def test_team_planer_can_delete_team_wish(self, db_session):
        planer, _planer_emp, team = _make_planer(db_session)
        _member, wish = _team_member_with_wish(db_session, team)
        DeleteShiftWish.role.check(planer, db_session, {"id": wish.id})


class TestUpdateShiftRoleCheck:
    def _shift_for(self, db_session, employee_id, name="ShiftSched"):
        s = Schedule(name=_u(name), status="draft", week_type="both")
        db_session.add(s)
        db_session.commit()
        sp = Shiftplan(
            schedule_id=s.id,
            employee_id=employee_id,
            date=_date(2026, 6, 1),
            shift_id="morning",
            start_time=_time(8, 0),
            end_time=_time(16, 0),
        )
        db_session.add(sp)
        db_session.commit()
        return sp

    def test_regular_user_denied(self, db_session, regular_user):
        sp = self._shift_for(db_session, 1)
        with pytest.raises(HTTPException) as e:
            UpdateShift.role.check(regular_user, db_session, {"id": sp.id})
        assert e.value.status_code == 403

    def test_employee_user_denied(self, db_session, employee_user):
        sp = self._shift_for(db_session, employee_user.employee_id)
        with pytest.raises(HTTPException) as e:
            UpdateShift.role.check(employee_user, db_session, {"id": sp.id})
        assert e.value.status_code == 403

    def test_planer_team_schedule_allowed(self, db_session):
        planer, _planer_emp, team = _make_planer(db_session)
        member, _wish = _team_member_with_wish(db_session, team)
        sp = self._shift_for(db_session, member.id)
        UpdateShift.role.check(planer, db_session, {"id": sp.id})

    def test_planer_foreign_schedule_denied(self, db_session, employee_user):
        planer, _planer_emp, _team = _make_planer(db_session)
        sp = self._shift_for(db_session, employee_user.employee_id, name="ForeignSched")
        with pytest.raises(HTTPException) as e:
            UpdateShift.role.check(planer, db_session, {"id": sp.id})
        assert e.value.status_code == 403

    def test_planer_cannot_reassign_to_foreign_employee(self, db_session, employee_user):
        planer, _planer_emp, team = _make_planer(db_session)
        member, _wish = _team_member_with_wish(db_session, team)
        sp = self._shift_for(db_session, member.id)
        with pytest.raises(HTTPException) as e:
            UpdateShift.role.check(planer, db_session, {"id": sp.id, "employee_id": employee_user.employee_id})
        assert e.value.status_code == 403
