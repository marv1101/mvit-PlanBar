"""Unit tests for the per-category DSGVO data collectors.

These tests target the SRP-split functions in ``gdpr_collectors`` — each
collector should be independently testable without the full export pipeline.
"""

import uuid
from datetime import UTC, date, datetime

from app.db.models.audit_log import AuditLog
from app.db.models.employee import Contract, Employee, Timecard
from app.db.models.pinboard import PinboardMessage, PinboardThread
from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User
from app.services.gdpr_collectors import (
    collect_audit_logs,
    collect_employee_contracts,
    collect_employee_shift_wishes,
    collect_employee_shiftplans,
    collect_employee_timecards,
    collect_employees,
    collect_pinboard,
    collect_user,
    serialize_date,
    serialize_datetime,
)


def _unique_user(db_session) -> User:
    """Create a fresh user with a unique email/username to avoid UNIQUE collisions."""
    tag = uuid.uuid4().hex[:8]
    user = User(
        username=f"u_{tag}",
        email=f"u_{tag}@x.com",
        password_hash="x",
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _unique_employee(db_session, user: User, tag: str | None = None) -> Employee:
    suffix = tag or uuid.uuid4().hex[:8]
    employee = Employee(
        first_name="Max",
        last_name=f"M_{suffix}",
        email=f"max_{suffix}@x.com",
        color="#FF0000",
        user_id=user.id,
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)
    return employee


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


class TestSerializers:
    def test_serialize_datetime_with_value(self):
        dt = datetime(2026, 7, 21, 12, 30, 0, tzinfo=UTC)
        assert serialize_datetime(dt) == "2026-07-21T12:30:00+00:00"

    def test_serialize_datetime_none(self):
        assert serialize_datetime(None) is None

    def test_serialize_date_with_value(self):
        assert serialize_date(date(2026, 7, 21)) == "2026-07-21"

    def test_serialize_date_none(self):
        assert serialize_date(None) is None


# ---------------------------------------------------------------------------
# collect_user
# ---------------------------------------------------------------------------


class TestCollectUser:
    def test_collect_user_returns_profile_block(self, db_session):
        user = _unique_user(db_session)

        result = collect_user(db_session, user.id)
        assert result is not None
        assert result["id"] == user.id
        assert result["username"] == user.username
        assert result["email"] == user.email
        assert result["role"] == "user"
        # created_at/updated_at are set by the DB / on_flush_mappers
        assert "created_at" in result
        assert "updated_at" in result
        assert "last_login" in result  # may be None

    def test_collect_user_returns_none_for_missing_id(self, db_session):
        assert collect_user(db_session, 999_999) is None


# ---------------------------------------------------------------------------
# collect_employee_* helpers
# ---------------------------------------------------------------------------


class TestCollectEmployeeContracts:
    def test_collects_contracts_with_serialized_dates(self, db_session):
        user = _unique_user(db_session)
        employee = _unique_employee(db_session, user)
        contract = Contract(
            employee_id=employee.id,
            weekly_working_hours=40.0,
            break_time=30,
            hired_role="Developer",
        )
        db_session.add(contract)
        db_session.commit()
        db_session.refresh(employee)

        rows = collect_employee_contracts(employee)
        assert len(rows) == 1
        row = rows[0]
        assert row["weekly_working_hours"] == 40.0
        assert row["break_time"] == 30
        assert row["hired_role"] == "Developer"
        # created_at/updated_at come from DB defaults
        assert "created_at" in row
        assert "updated_at" in row

    def test_returns_empty_list_when_no_contracts(self, db_session):
        user = _unique_user(db_session)
        employee = _unique_employee(db_session, user)
        assert collect_employee_contracts(employee) == []


class TestCollectEmployeeTimecards:
    def test_collects_timecard_fields(self, db_session):
        user = _unique_user(db_session)
        employee = _unique_employee(db_session, user)

        tc = Timecard(
            employee_id=employee.id,
            week=29,
            year=2026,
            balance=2.5,
            scheduled_hours=40.0,
            actual_hours=42.5,
            contract_hours=40.0,
            manual_adjustment_hours=0.0,
            adjustment_reason=None,
        )
        db_session.add(tc)
        db_session.commit()
        db_session.refresh(employee)

        rows = collect_employee_timecards(employee)
        assert len(rows) == 1
        assert rows[0]["week"] == 29
        assert rows[0]["year"] == 2026
        assert rows[0]["balance"] == 2.5
        assert rows[0]["actual_hours"] == 42.5
        assert "adjustment_reason" in rows[0]

    def test_returns_empty_when_no_timecards(self, db_session):
        user = _unique_user(db_session)
        employee = _unique_employee(db_session, user)
        assert collect_employee_timecards(employee) == []


class TestCollectEmployeeShiftWishes:
    def test_serializes_date_field(self, db_session):
        user = _unique_user(db_session)
        employee = _unique_employee(db_session, user)

        sw = ShiftWish(
            employee_id=employee.id,
            date=date(2026, 8, 1),
            week="A",
            type="preference",
            note="no nights",
            status="pending",
        )
        db_session.add(sw)
        db_session.commit()
        db_session.refresh(employee)

        rows = collect_employee_shift_wishes(employee)
        assert len(rows) == 1
        assert rows[0]["date"] == "2026-08-01"
        assert rows[0]["type"] == "preference"
        assert rows[0]["status"] == "pending"
        # Datetime fields present (may be None)
        assert "reviewed_at" in rows[0]
        assert "created_at" in rows[0]

    def test_returns_empty_when_no_wishes(self, db_session):
        user = _unique_user(db_session)
        employee = _unique_employee(db_session, user)
        assert collect_employee_shift_wishes(employee) == []


class TestCollectEmployeeShiftplans:
    def test_returns_empty_when_no_shiftplans(self, db_session):
        user = _unique_user(db_session)
        employee = _unique_employee(db_session, user)
        # No shiftplans seeded
        assert collect_employee_shiftplans(db_session, employee) == []


# ---------------------------------------------------------------------------
# collect_employees (orchestrator)
# ---------------------------------------------------------------------------


class TestCollectEmployees:
    def test_returns_empty_for_user_without_employees(self, db_session):
        user = _unique_user(db_session)

        assert collect_employees(db_session, user) == []

    def test_includes_nested_subcollections(self, db_session):
        user = _unique_user(db_session)
        employee = _unique_employee(db_session, user)
        db_session.add(Contract(employee_id=employee.id, weekly_working_hours=40.0))
        db_session.add(ShiftWish(employee_id=employee.id, date=date(2026, 8, 1), week="A", type="p", status="p"))
        db_session.commit()
        db_session.refresh(employee)

        rows = collect_employees(db_session, user)
        assert len(rows) == 1
        assert rows[0]["first_name"] == "Max"
        assert isinstance(rows[0]["contracts"], list)
        assert isinstance(rows[0]["timecards"], list)
        assert isinstance(rows[0]["shift_wishes"], list)
        assert isinstance(rows[0]["shiftplans"], list)
        assert len(rows[0]["contracts"]) == 1
        assert len(rows[0]["shift_wishes"]) == 1

    def test_includes_employee_linked_via_user_employee_id(self, db_session):
        """A user may be linked via user.employee_id (not just employee.user_id)."""
        user = _unique_user(db_session)

        # Create an employee with NO user_id back-link, but linked via the user's employee_id
        employee = Employee(first_name="Ind", last_name="Ee", email="i@x.com")
        db_session.add(employee)
        db_session.commit()
        db_session.refresh(employee)
        user.employee_id = employee.id
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        rows = collect_employees(db_session, user)
        assert len(rows) == 1
        assert rows[0]["id"] == employee.id


# ---------------------------------------------------------------------------
# collect_pinboard
# ---------------------------------------------------------------------------


class TestCollectPinboard:
    def test_returns_threads_and_messages_for_user(self, db_session):
        user = _unique_user(db_session)

        thread = PinboardThread(author_id=user.id, title="My Thread", is_pinned=False)
        db_session.add(thread)
        db_session.commit()
        db_session.refresh(thread)
        db_session.add(PinboardMessage(thread_id=thread.id, author_id=user.id, content="hi"))
        db_session.commit()

        result = collect_pinboard(db_session, user.id)
        assert len(result["threads"]) == 1
        assert result["threads"][0]["title"] == "My Thread"
        assert len(result["messages"]) == 1
        assert result["messages"][0]["content"] == "hi"

    def test_returns_empty_lists_for_user_with_no_pinboard(self, db_session):
        user = _unique_user(db_session)

        result = collect_pinboard(db_session, user.id)
        assert result == {"threads": [], "messages": []}


# ---------------------------------------------------------------------------
# collect_audit_logs
# ---------------------------------------------------------------------------


class TestCollectAuditLogs:
    def test_dedupes_actor_and_resource_logs(self, db_session):
        user = _unique_user(db_session)

        # Log where the user is the actor
        a1 = AuditLog(
            user_id=user.id,
            action="login",
            resource_type="user",
            resource_id=str(user.id),
            details="signin",
            ip_address="127.0.0.1",
        )
        # Log where the user is the resource but not the actor
        a2 = AuditLog(
            user_id=None,
            action="profile_updated",
            resource_type="user",
            resource_id=str(user.id),
            details="by admin",
            ip_address="10.0.0.1",
        )
        # Unrelated log
        a3 = AuditLog(
            user_id=None,
            action="other",
            resource_type="schedule",
            resource_id="42",
            details="x",
            ip_address="127.0.0.1",
        )
        db_session.add_all([a1, a2, a3])
        db_session.commit()

        logs = collect_audit_logs(db_session, user.id)
        ids = {entry["id"] for entry in logs}
        # a1 and a2 both reference user, a3 does not
        assert a1.id in ids
        assert a2.id in ids
        assert a3.id not in ids
        # Sorted ascending by created_at
        timestamps = [entry["created_at"] for entry in logs]
        assert timestamps == sorted(timestamps)

    def test_returns_empty_list_for_user_with_no_logs(self, db_session):
        user = _unique_user(db_session)

        assert collect_audit_logs(db_session, user.id) == []

    def test_includes_required_fields(self, db_session):
        user = _unique_user(db_session)
        db_session.add(
            AuditLog(
                user_id=user.id,
                action="test",
                resource_type="user",
                resource_id=str(user.id),
                details="d",
                ip_address="1.2.3.4",
            )
        )
        db_session.commit()

        [row] = collect_audit_logs(db_session, user.id)
        for key in ("id", "action", "resource_type", "resource_id", "details", "ip_address", "created_at"):
            assert key in row
        assert row["action"] == "test"
        assert row["ip_address"] == "1.2.3.4"
