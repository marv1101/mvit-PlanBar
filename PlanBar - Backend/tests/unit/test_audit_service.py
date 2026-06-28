from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.user import User
from app.services import audit_service


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


def create_user(db_session, username="testuser", email="test@test.com"):
    user = User(
        username=username,
        email=email,
        password_hash="hash",
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestLogFunctions:
    def test_log_basic(self, db_session):
        entry = audit_service.log(
            db_session,
            user_id=1,
            action="TEST_ACTION",
            resource_type="test",
            resource_id="42",
            details="test details",
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )
        assert entry.id is not None
        assert entry.user_id == 1
        assert entry.action == "TEST_ACTION"
        assert entry.resource_type == "test"
        assert entry.resource_id == "42"
        assert entry.details == "test details"
        assert entry.ip_address == "127.0.0.1"
        assert entry.user_agent == "test-agent"
        assert entry.created_at is not None

    def test_log_nullable_fields(self, db_session):
        entry = audit_service.log(
            db_session,
            user_id=None,
            action="SYSTEM",
            resource_type="system",
        )
        assert entry.user_id is None
        assert entry.resource_id is None
        assert entry.details is None
        assert entry.ip_address is None
        assert entry.user_agent is None

    def test_log_create(self, db_session):
        entry = audit_service.log_create(db_session, user_id=1, resource_type="employee", resource_id="10")
        assert entry.action == "CREATE"

    def test_log_update(self, db_session):
        entry = audit_service.log_update(db_session, user_id=1, resource_type="employee", resource_id="10")
        assert entry.action == "UPDATE"

    def test_log_delete(self, db_session):
        entry = audit_service.log_delete(db_session, user_id=1, resource_type="employee", resource_id="10")
        assert entry.action == "DELETE"

    def test_log_access(self, db_session):
        entry = audit_service.log_access(db_session, user_id=1, resource_type="schedule", resource_id="5")
        assert entry.action == "ACCESS"


class TestQuery:
    def test_query_pagination_defaults(self, db_session):
        for i in range(25):
            audit_service.log(db_session, user_id=None, action="TEST", resource_type="test")
        items, pagination = audit_service.query(db_session)
        assert len(items) == 20
        assert pagination["total"] == 25
        assert pagination["offset"] == 0
        assert pagination["limit"] == 20

    def test_query_with_user_filter(self, db_session):
        audit_service.log(db_session, user_id=1, action="TEST", resource_type="test")
        audit_service.log(db_session, user_id=2, action="TEST", resource_type="test")
        items, pagination = audit_service.query(db_session, user_id=1)
        assert len(items) == 1
        assert items[0].user_id == 1

    def test_query_with_action_filter(self, db_session):
        audit_service.log(db_session, user_id=None, action="CREATE", resource_type="test")
        audit_service.log(db_session, user_id=None, action="DELETE", resource_type="test")
        items, _ = audit_service.query(db_session, action="CREATE")
        assert len(items) == 1
        assert items[0].action == "CREATE"

    def test_query_with_resource_type_filter(self, db_session):
        audit_service.log(db_session, user_id=None, action="TEST", resource_type="employee")
        audit_service.log(db_session, user_id=None, action="TEST", resource_type="schedule")
        items, _ = audit_service.query(db_session, resource_type="employee")
        assert len(items) == 1

    def test_query_with_resource_id_filter(self, db_session):
        audit_service.log(
            db_session,
            user_id=None,
            action="TEST",
            resource_type="test",
            resource_id="100",
        )
        audit_service.log(
            db_session,
            user_id=None,
            action="TEST",
            resource_type="test",
            resource_id="200",
        )
        items, _ = audit_service.query(db_session, resource_id="100")
        assert len(items) == 1

    def test_query_with_date_range(self, db_session):
        audit_service.log(db_session, user_id=None, action="TEST", resource_type="test")
        now = datetime.now(timezone.utc)
        items, _ = audit_service.query(
            db_session,
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1),
        )
        assert len(items) >= 1


class TestSuspiciousPatterns:
    def test_brute_force_detection(self, db_session):
        for _ in range(5):
            audit_service.log(
                db_session,
                user_id=None,
                action="LOGIN_FAILED",
                resource_type="user",
                resource_id="test@test.com",
                ip_address="192.168.1.1",
            )
        patterns = audit_service.get_suspicious_patterns(db_session)
        brute_force = [p for p in patterns if p["pattern_type"] == "brute_force"]
        assert len(brute_force) >= 1
        assert brute_force[0]["count"] >= 5

    def test_no_suspicious_patterns(self, db_session):
        audit_service.log(db_session, user_id=1, action="LOGIN_FAILED", resource_type="user")
        patterns = audit_service.get_suspicious_patterns(db_session)
        assert len(patterns) == 0

    def test_non_existent_user_detection(self, db_session):
        for _ in range(3):
            audit_service.log(
                db_session,
                user_id=None,
                action="LOGIN_FAILED",
                resource_type="user",
                resource_id="unknown@test.com",
            )
        patterns = audit_service.get_suspicious_patterns(db_session)
        non_existent = [p for p in patterns if p["pattern_type"] == "non_existent_user"]
        assert len(non_existent) >= 1

    def test_rapid_operations_detection(self, db_session):
        user = create_user(db_session)
        for _ in range(50):
            audit_service.log(
                db_session,
                user_id=user.id,
                action="CREATE",
                resource_type="test",
                resource_id="1",
            )
        patterns = audit_service.get_suspicious_patterns(db_session)
        rapid = [p for p in patterns if p["pattern_type"] == "rapid_operations"]
        assert len(rapid) >= 1
