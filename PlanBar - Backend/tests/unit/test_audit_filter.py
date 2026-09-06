"""Tests for AuditLogFilter schema and query_with_filter function."""
from datetime import datetime, timezone

from app.schemas.audit import AuditLogFilter
from app.services import audit_service


class TestAuditLogFilter:
    def test_default_values(self):
        """AuditLogFilter has all None defaults."""
        f = AuditLogFilter()
        assert f.user_id is None
        assert f.action is None
        assert f.resource_type is None
        assert f.resource_id is None
        assert f.start_date is None
        assert f.end_date is None

    def test_all_fields_populated(self):
        """AuditLogFilter accepts all fields."""
        now = datetime.now(timezone.utc)
        f = AuditLogFilter(
            user_id=42,
            action="CREATE",
            resource_type="schedule",
            resource_id="100",
            start_date=now,
            end_date=now,
        )
        assert f.user_id == 42
        assert f.action == "CREATE"
        assert f.resource_type == "schedule"
        assert f.resource_id == "100"
        assert f.start_date == now
        assert f.end_date == now

    def test_partial_fields(self):
        """AuditLogFilter works with partial fields."""
        f = AuditLogFilter(action="DELETE", user_id=1)
        assert f.user_id == 1
        assert f.action == "DELETE"
        assert f.resource_type is None
        assert f.resource_id is None

    def test_to_dict_filters_none_values(self):
        """to_dict returns only non-None values."""
        f = AuditLogFilter(action="CREATE")
        d = f.to_dict()
        assert d == {"action": "CREATE"}

    def test_to_dict_empty(self):
        """to_dict returns empty dict when all None."""
        f = AuditLogFilter()
        assert f.to_dict() == {}


class TestQueryWithFilter:
    def test_no_filters(self, db_session):
        """query_with_filter with empty filter returns all."""
        audit_service.log(db_session, user_id=99901, action="TEST_NO_FILTER_1", resource_type="test_x")
        audit_service.log(db_session, user_id=99902, action="TEST_NO_FILTER_2", resource_type="test_x")
        f = AuditLogFilter()
        items, pagination = audit_service.query_with_filter(db_session, f)
        assert pagination["total"] >= 2

    def test_filter_by_action(self, db_session):
        """query_with_filter filters by action."""
        audit_service.log(db_session, user_id=99903, action="TEST_FILTER_ACTION_A", resource_type="test_x")
        audit_service.log(db_session, user_id=99903, action="TEST_FILTER_ACTION_B", resource_type="test_x")
        f = AuditLogFilter(action="TEST_FILTER_ACTION_A")
        items, _ = audit_service.query_with_filter(db_session, f)
        assert all(item.action == "TEST_FILTER_ACTION_A" for item in items)
        assert len(items) >= 1

    def test_filter_by_user_id(self, db_session):
        """query_with_filter filters by user_id."""
        audit_service.log(db_session, user_id=99904, action="TEST_FILTER_UID", resource_type="test_x")
        audit_service.log(db_session, user_id=99905, action="TEST_FILTER_UID", resource_type="test_x")
        f = AuditLogFilter(user_id=99904)
        items, _ = audit_service.query_with_filter(db_session, f)
        assert all(item.user_id == 99904 for item in items)
        assert len(items) >= 1

    def test_filter_by_resource_type(self, db_session):
        """query_with_filter filters by resource_type."""
        audit_service.log(db_session, user_id=99906, action="TEST_FILTER_RT", resource_type="test_resource_alpha")
        audit_service.log(db_session, user_id=99906, action="TEST_FILTER_RT", resource_type="test_resource_beta")
        f = AuditLogFilter(resource_type="test_resource_alpha")
        items, _ = audit_service.query_with_filter(db_session, f)
        assert all(item.resource_type == "test_resource_alpha" for item in items)
        assert len(items) >= 1

    def test_combined_filters(self, db_session):
        """query_with_filter handles multiple filters."""
        # Use unique identifiers to avoid collision with other tests
        audit_service.log(db_session, user_id=99907, action="TEST_COMBINED_A", resource_type="test_combo")
        audit_service.log(db_session, user_id=99907, action="TEST_COMBINED_B", resource_type="test_combo")
        audit_service.log(db_session, user_id=99908, action="TEST_COMBINED_A", resource_type="test_combo")
        f = AuditLogFilter(user_id=99907, action="TEST_COMBINED_A")
        items, _ = audit_service.query_with_filter(db_session, f)
        assert len(items) == 1
        assert items[0].user_id == 99907
        assert items[0].action == "TEST_COMBINED_A"

    def test_backward_compat_query(self, db_session):
        """Old query() function still works."""
        audit_service.log(db_session, user_id=99909, action="TEST_BACKWARD", resource_type="test_x")
        items, pagination = audit_service.query(db_session, action="TEST_BACKWARD")
        assert len(items) >= 1
        assert all(item.action == "TEST_BACKWARD" for item in items)
