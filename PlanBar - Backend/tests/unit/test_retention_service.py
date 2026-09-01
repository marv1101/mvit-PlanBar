from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.audit_log import AuditLog
from app.db.models.employee import Employee, Timecard
from app.db.models.pinboard import PinboardThread
from app.db.models.retention_audit import RetentionAuditLog
from app.db.models.schedule import Schedule
from app.db.models.shift_swap import ShiftSwapRequest
from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User
from app.services.retention_service import (
    RETENTION_RULES,
    cleanup_expired_data,
    get_policies,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


def _make_user(db, username="test", email="test@test.com", last_login=None):
    user = User(
        username=username,
        email=email,
        password_hash="hash",
        role="user",
        last_login=last_login,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_employee(db, user_id=None, updated_at=None):
    emp = Employee(
        first_name="Test",
        last_name="Employee",
        user_id=user_id,
    )
    if updated_at:
        emp.updated_at = updated_at
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


def _make_audit_log(db, action="TEST", created_at=None):
    entry = AuditLog(
        action=action,
        resource_type="test",
        resource_id="1",
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _make_timecard(db, employee_id, created_at=None):
    tc = Timecard(
        employee_id=employee_id,
        week=1,
        year=2024,
        balance=0.0,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)
    return tc


def _make_shift_wish(db, employee_id, status="approved", wish_type="preferred", updated_at=None):
    sw = ShiftWish(
        employee_id=employee_id,
        date=datetime.now(timezone.utc).date(),
        type=wish_type,
        status=status,
        updated_at=updated_at or datetime.now(timezone.utc),
    )
    db.add(sw)
    db.commit()
    db.refresh(sw)
    return sw


def _make_pinboard_thread(db, author_id, updated_at=None):
    thread = PinboardThread(
        title="Test",
        author_id=author_id,
        updated_at=updated_at or datetime.now(timezone.utc),
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


def _make_schedule(db, end_date=None):
    sched = Schedule(
        name="Test Schedule",
        status="completed",
        end_date=end_date,
    )
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return sched


def _make_shift_swap(db, status="approved", updated_at=None):
    swap = ShiftSwapRequest(
        employee_id=1,
        requester_shift_id=1,
        target_employee_id=2,
        target_shift_id=2,
        status=status,
        updated_at=updated_at or datetime.now(timezone.utc),
    )
    db.add(swap)
    db.commit()
    db.refresh(swap)
    return swap


class TestRetentionRulesComplete:
    def test_all_required_categories_present(self):
        expected = {
            "user_inactive",
            "employee_separated",
            "timecards",
            "auth_logs",
            "audit_logs",
            "schedules_completed",
            "shift_wishes_processed",
            "vacation_requests",
            "pinboard_entries",
            "shift_swap_requests",
        }
        assert expected == set(RETENTION_RULES.keys())

    def test_each_rule_has_required_fields(self):
        required_fields = {"category", "description", "retention_days", "action", "table", "legal_basis"}
        for key, rule in RETENTION_RULES.items():
            missing = required_fields - set(rule.keys())
            assert not missing, f"Rule '{key}' missing fields: {missing}"

    def test_retention_days_are_positive(self):
        for key, rule in RETENTION_RULES.items():
            assert rule["retention_days"] > 0, f"Rule '{key}' has non-positive retention_days"

    def test_actions_are_valid(self):
        for key, rule in RETENTION_RULES.items():
            assert rule["action"] in ("delete", "pseudonymize"), (
                f"Rule '{key}' has invalid action: {rule['action']}"
            )


class TestPseudonymizeUser:
    def test_sets_placeholders(self, db_session):
        user = _make_user(db_session, username="realname", email="real@example.com")
        cleanup_expired_data(db_session, dry_run=True)

        # Manually test pseudonymization logic
        from app.services.retention_service import _pseudonymize_user
        _pseudonymize_user(user, db_session)
        db_session.commit()

        assert "[GELÖSCHT-" in user.username
        assert user.email.endswith("@deleted.local")
        assert user.password_hash == "DELETED"
        assert user.role == "user"
        assert user.last_login is None

    def test_pseudonymize_inactive_user_6_months(self, db_session):
        old_login = datetime.now(timezone.utc) - timedelta(days=181)
        user = _make_user(db_session, last_login=old_login)

        report = cleanup_expired_data(db_session, dry_run=False)
        assert "user" in report
        assert report["user"]["pseudonymized"] == 1

        db_session.refresh(user)
        assert "[GELÖSCHT-" in user.username


class TestDeleteOldRequestLogs:
    def test_delete_old_audit_logs_3_years(self, db_session):
        old_date = datetime.now(timezone.utc) - timedelta(days=1096)
        _make_audit_log(db_session, action="TEST_ACTION", created_at=old_date)
        _make_audit_log(db_session, action="TEST_ACTION", created_at=datetime.now(timezone.utc))

        report = cleanup_expired_data(db_session, dry_run=False)
        assert "audit_log" in report
        assert report["audit_log"]["deleted"] == 1

        remaining = db_session.query(AuditLog).filter(AuditLog.action == "TEST_ACTION").all()
        assert len(remaining) == 1


class TestDeleteOldAuthLogs:
    def test_delete_old_auth_logs_1_year(self, db_session):
        old_date = datetime.now(timezone.utc) - timedelta(days=366)
        _make_audit_log(db_session, action="LOGIN_SUCCESS", created_at=old_date)
        _make_audit_log(db_session, action="LOGIN_FAILED", created_at=old_date)
        _make_audit_log(db_session, action="LOGOUT", created_at=old_date)
        _make_audit_log(db_session, action="LOGIN_SUCCESS", created_at=datetime.now(timezone.utc))

        report = cleanup_expired_data(db_session, dry_run=False)
        assert "auth_log" in report
        assert report["auth_log"]["deleted"] == 3

        remaining = db_session.query(AuditLog).filter(AuditLog.action == "LOGIN_SUCCESS").all()
        assert len(remaining) == 1


class TestDeleteEmployeeAfter10Years:
    def test_pseudonymize_old_separated_employee(self, db_session):
        old_date = datetime.now(timezone.utc) - timedelta(days=3651)
        emp = _make_employee(db_session, user_id=None, updated_at=old_date)

        report = cleanup_expired_data(db_session, dry_run=False)
        assert "employee" in report
        assert report["employee"]["pseudonymized"] == 1

        db_session.refresh(emp)
        assert emp.first_name == "Gelöscht"
        assert "[GELÖSCHT-" in emp.last_name

    def test_does_not_touch_active_employee(self, db_session):
        user = _make_user(db_session)
        _make_employee(db_session, user_id=user.id)  # active employee, must stay

        report = cleanup_expired_data(db_session, dry_run=False)
        if "employee" in report:
            assert report["employee"]["pseudonymized"] == 0


class TestAuditLogWrittenOnAction:
    def test_audit_log_created_on_pseudonymization(self, db_session):
        old_login = datetime.now(timezone.utc) - timedelta(days=181)
        _make_user(db_session, last_login=old_login)

        cleanup_expired_data(db_session, dry_run=False)

        audit_entries = db_session.query(RetentionAuditLog).filter(
            RetentionAuditLog.category == "user",
            RetentionAuditLog.action == "pseudonymized",
        ).all()
        assert len(audit_entries) == 1
        assert audit_entries[0].reason == "retention_policy_6_months"
        assert audit_entries[0].executed_by == "system"

    def test_audit_log_created_on_deletion(self, db_session):
        old_date = datetime.now(timezone.utc) - timedelta(days=1096)
        _make_audit_log(db_session, action="TEST_ACTION", created_at=old_date)

        cleanup_expired_data(db_session, dry_run=False)

        audit_entries = db_session.query(RetentionAuditLog).filter(
            RetentionAuditLog.category == "audit_log",
            RetentionAuditLog.action == "deleted",
        ).all()
        assert len(audit_entries) == 1
        assert audit_entries[0].reason == "retention_policy_3_years"


class TestAuditLogContainsNoPii:
    def test_record_id_is_pseudonymized(self, db_session):
        old_login = datetime.now(timezone.utc) - timedelta(days=181)
        _make_user(db_session, last_login=old_login)

        cleanup_expired_data(db_session, dry_run=False)

        audit_entries = db_session.query(RetentionAuditLog).all()
        for entry in audit_entries:
            # record_id should be a hex tag, not a username or email
            assert "@" not in entry.record_id
            assert entry.record_id.isalnum() or entry.record_id.isdigit()


class TestDryRunReturnsNoSideEffects:
    def test_dry_run_does_not_delete(self, db_session):
        old_date = datetime.now(timezone.utc) - timedelta(days=1096)
        _make_audit_log(db_session, action="TEST_ACTION", created_at=old_date)

        report = cleanup_expired_data(db_session, dry_run=True)

        if "audit_log" in report:
            assert report["audit_log"]["deleted"] == 1

        # No actual deletion
        remaining = db_session.query(AuditLog).filter(AuditLog.action == "TEST_ACTION").all()
        assert len(remaining) == 1

    def test_dry_run_does_not_pseudonymize(self, db_session):
        old_login = datetime.now(timezone.utc) - timedelta(days=181)
        user = _make_user(db_session, last_login=old_login)

        cleanup_expired_data(db_session, dry_run=True)

        # No pseudonymization happened
        db_session.refresh(user)
        assert user.username == "test"
        assert user.email == "test@test.com"

    def test_dry_run_creates_no_audit_logs(self, db_session):
        old_login = datetime.now(timezone.utc) - timedelta(days=181)
        _make_user(db_session, last_login=old_login)

        cleanup_expired_data(db_session, dry_run=True)

        audit_entries = db_session.query(RetentionAuditLog).all()
        assert len(audit_entries) == 0


class TestGetPolicies:
    def test_returns_all_rules(self):
        policies = get_policies()
        assert len(policies) == len(RETENTION_RULES)

    def test_policy_has_key_fields(self):
        policies = get_policies()
        for policy in policies:
            assert "key" in policy
            assert "category" in policy
            assert "description" in policy
            assert "retention_days" in policy
            assert "action" in policy
            assert "legal_basis" in policy
