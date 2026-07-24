"""Integration tests for the in-app notification system."""


# ---------------------------------------------------------------------------
# Helper to create an employee linked to a user and return (headers, emp_id)
# ---------------------------------------------------------------------------
def _setup_employee_user(client, db_session, auth_headers, prefix):
    """Create a separate user linked to a new employee, return (emp_headers, emp_id)."""
    from app.db.models.user import User

    register_data = {
        "username": f"{prefix}user",
        "email": f"{prefix}@test.com",
        "password": "TestPass@123",
    }
    client.post("/api/v1/users", json=register_data, headers=auth_headers)
    user = db_session.query(User).filter(User.email == f"{prefix}@test.com").first()

    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": f"Emp{prefix}", "last_name": "Test"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    # Link both sides: user -> employee AND employee -> user
    user.employee_id = emp_id
    db_session.add(user)
    db_session.commit()

    from app.db.models.employee import Employee

    employee = db_session.query(Employee).filter(Employee.id == emp_id).first()
    employee.user_id = user.id
    db_session.add(employee)
    db_session.commit()

    login_resp = client.post(
        "/api/v1/users/login",
        json={"email": f"{prefix}@test.com", "password": "TestPass@123"},
    )
    token = login_resp.json()["access_token"]
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}, emp_id


def _clean_notifications(db_session):
    """Remove all notifications to avoid cross-test contamination."""
    from app.db.models.notification import Notification

    db_session.query(Notification).delete()
    db_session.commit()


# ---------------------------------------------------------------------------
# Notification API endpoint tests
# ---------------------------------------------------------------------------
class TestNotificationEndpoints:
    """Tests for GET /notifications, GET /unread-count, PUT /read, PUT /read-all."""

    def test_list_notifications_empty(self, client, auth_headers, db_session):
        _clean_notifications(db_session)
        resp = client.get("/api/v1/notifications", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_unread_count_empty(self, client, auth_headers, db_session):
        _clean_notifications(db_session)
        resp = client.get("/api/v1/notifications/unread-count", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_create_and_list_notification(self, client, db_session, auth_headers):
        _clean_notifications(db_session)
        from app.db.models.notification import Notification
        from app.db.models.user import User

        user = db_session.query(User).filter(User.email == "admin@test.com").first()

        n = Notification(
            user_id=user.id,
            type="wish_approved",
            title="Wunsch genehmigt",
            message="Dein Wunsch wurde genehmigt.",
            read=False,
            data={"wish_id": 1},
        )
        db_session.add(n)
        db_session.commit()
        db_session.refresh(n)

        resp = client.get("/api/v1/notifications", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["type"] == "wish_approved"
        assert data["items"][0]["read"] is False
        assert data["items"][0]["data"]["wish_id"] == 1

    def test_unread_count(self, client, db_session, auth_headers):
        _clean_notifications(db_session)
        from app.db.models.notification import Notification
        from app.db.models.user import User

        user = db_session.query(User).filter(User.email == "admin@test.com").first()

        for i in range(3):
            db_session.add(
                Notification(
                    user_id=user.id,
                    type="shift_changed",
                    title=f"Shift {i}",
                    message=f"Message {i}",
                    read=False,
                )
            )
        db_session.add(
            Notification(
                user_id=user.id,
                type="wish_approved",
                title="Old",
                message="Already read",
                read=True,
            )
        )
        db_session.commit()

        resp = client.get("/api/v1/notifications/unread-count", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["count"] == 3

    def test_filter_unread_only(self, client, db_session, auth_headers):
        _clean_notifications(db_session)
        from app.db.models.notification import Notification
        from app.db.models.user import User

        user = db_session.query(User).filter(User.email == "admin@test.com").first()

        db_session.add(Notification(user_id=user.id, type="wish_approved", title="Read", message="m", read=True))
        db_session.add(Notification(user_id=user.id, type="wish_rejected", title="Unread", message="m", read=False))
        db_session.commit()

        resp = client.get("/api/v1/notifications?unread_only=true", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Unread"

    def test_mark_as_read(self, client, db_session, auth_headers):
        _clean_notifications(db_session)
        from app.db.models.notification import Notification
        from app.db.models.user import User

        user = db_session.query(User).filter(User.email == "admin@test.com").first()

        n = Notification(user_id=user.id, type="shift_changed", title="T", message="M", read=False)
        db_session.add(n)
        db_session.commit()
        db_session.refresh(n)

        resp = client.put(f"/api/v1/notifications/{n.id}/read", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["read"] is True

        # Verify via count
        resp2 = client.get("/api/v1/notifications/unread-count", headers=auth_headers)
        assert resp2.json()["count"] == 0

    def test_mark_all_read(self, client, db_session, auth_headers):
        _clean_notifications(db_session)
        from app.db.models.notification import Notification
        from app.db.models.user import User

        user = db_session.query(User).filter(User.email == "admin@test.com").first()

        for _ in range(5):
            db_session.add(Notification(user_id=user.id, type="wish_approved", title="T", message="M", read=False))
        db_session.commit()

        resp = client.put("/api/v1/notifications/read-all", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["marked"] == 5

        resp2 = client.get("/api/v1/notifications/unread-count", headers=auth_headers)
        assert resp2.json()["count"] == 0

    def test_mark_nonexistent_notification(self, client, auth_headers):
        resp = client.put("/api/v1/notifications/99999/read", headers=auth_headers)
        assert resp.status_code == 404

    def test_mark_other_users_notification_forbidden(self, client, db_session, auth_headers):
        _clean_notifications(db_session)
        from app.db.models.notification import Notification
        from app.db.models.user import User

        # Create another user
        client.post(
            "/api/v1/users",
            json={"username": "other_noti", "email": "other_noti@test.com", "password": "TestPass@123"},
            headers=auth_headers,
        )
        other_user = db_session.query(User).filter(User.email == "other_noti@test.com").first()

        n = Notification(
            user_id=other_user.id,
            type="wish_approved",
            title="T",
            message="M",
            read=False,
        )
        db_session.add(n)
        db_session.commit()
        db_session.refresh(n)

        resp = client.put(f"/api/v1/notifications/{n.id}/read", headers=auth_headers)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Integration: wish approval creates notification
# ---------------------------------------------------------------------------
class TestWishApprovalNotification:
    def test_approve_wish_creates_notification(self, client, auth_headers, db_session):
        _clean_notifications(db_session)
        emp_headers, emp_id = _setup_employee_user(client, db_session, auth_headers, "notiemp1")

        # Create a wish for the employee
        create_resp = client.post(
            "/api/v1/requests",
            json={
                "employee_id": emp_id,
                "date": "2026-07-01",
                "type": "preferred",
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        wish_id = create_resp.json()["id"]

        # Approve it (admin)
        approve_resp = client.put(f"/api/v1/requests/{wish_id}/approve", headers=auth_headers)
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "approved"

        # Employee should see a notification
        noti_resp = client.get("/api/v1/notifications", headers=emp_headers)
        assert noti_resp.status_code == 200
        notis = noti_resp.json()["items"]
        wish_notis = [n for n in notis if n["type"] == "wish_approved"]
        assert len(wish_notis) == 1
        assert "genehmigt" in wish_notis[0]["message"].lower()

    def test_reject_wish_creates_notification(self, client, auth_headers, db_session):
        _clean_notifications(db_session)
        emp_headers, emp_id = _setup_employee_user(client, db_session, auth_headers, "notiemp2")

        create_resp = client.post(
            "/api/v1/requests",
            json={
                "employee_id": emp_id,
                "date": "2026-07-02",
                "type": "unavailable",
            },
            headers=auth_headers,
        )
        wish_id = create_resp.json()["id"]

        reject_resp = client.put(
            f"/api/v1/requests/{wish_id}/reject",
            json={"rejection_reason": "Nicht genug Personal"},
            headers=auth_headers,
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["status"] == "rejected"

        noti_resp = client.get("/api/v1/notifications", headers=emp_headers)
        assert noti_resp.status_code == 200
        notis = noti_resp.json()["items"]
        reject_notis = [n for n in notis if n["type"] == "wish_rejected"]
        assert len(reject_notis) == 1
        assert "abgelehnt" in reject_notis[0]["message"].lower()


# ---------------------------------------------------------------------------
# Integration: schedule status change creates notification
# ---------------------------------------------------------------------------
class TestScheduleStatusNotification:
    def test_schedule_completed_notifies_assigned_employees(self, client, auth_headers, db_session):
        _clean_notifications(db_session)
        emp_headers, emp_id = _setup_employee_user(client, db_session, auth_headers, "schednoti1")

        # Create a schedule with a shiftplan for the employee
        schedule_resp = client.post(
            "/api/v1/schedules",
            json={
                "name": "Notification Schedule",
                "start_date": "2026-07-01",
                "end_date": "2026-07-07",
                "role_requirements": {"früh": "1"},
                "shiftplans": [
                    {
                        "employee_id": emp_id,
                        "date": "2026-07-01",
                        "shift_id": "früh",
                        "start_time": "06:00",
                        "end_time": "14:00",
                    },
                ],
            },
            headers=auth_headers,
        )
        schedule_id = schedule_resp.json()["id"]

        # Update status to completed
        update_resp = client.put(
            f"/api/v1/schedules/{schedule_id}",
            json={"status": "completed"},
            headers=auth_headers,
        )
        assert update_resp.status_code == 200

        # Employee should see a schedule_published notification
        noti_resp = client.get("/api/v1/notifications", headers=emp_headers)
        assert noti_resp.status_code == 200
        notis = noti_resp.json()["items"]
        sched_notis = [n for n in notis if n["type"] == "schedule_published"]
        assert len(sched_notis) == 1
        assert "Notification Schedule" in sched_notis[0]["message"]


# ---------------------------------------------------------------------------
# Integration: shift update creates notification
# ---------------------------------------------------------------------------
class TestShiftUpdateNotification:
    def test_shiftplan_update_notifies_employee(self, client, auth_headers, db_session):
        _clean_notifications(db_session)
        emp_headers, emp_id = _setup_employee_user(client, db_session, auth_headers, "shftnoti1")

        # Create a schedule with a shiftplan
        schedule_resp = client.post(
            "/api/v1/schedules",
            json={
                "name": "Shift Update Schedule",
                "start_date": "2026-07-10",
                "end_date": "2026-07-16",
                "role_requirements": {"früh": "1"},
                "shiftplans": [
                    {
                        "employee_id": emp_id,
                        "date": "2026-07-10",
                        "shift_id": "früh",
                        "start_time": "06:00",
                        "end_time": "14:00",
                    },
                ],
            },
            headers=auth_headers,
        )
        schedule_id = schedule_resp.json()["id"]

        # Get the shiftplan id
        shifts_resp = client.get(f"/api/v1/schedules/{schedule_id}/shifts", headers=auth_headers)
        shiftplan_id = shifts_resp.json()["items"][0]["id"]

        # Update the shift
        update_resp = client.put(
            f"/api/v1/schedules/{schedule_id}/shifts/{shiftplan_id}",
            json={"shift_id": "spät", "start_time": "14:00", "end_time": "22:00"},
            headers=auth_headers,
        )
        assert update_resp.status_code == 200

        # Employee should see a shift_changed notification
        noti_resp = client.get("/api/v1/notifications", headers=emp_headers)
        assert noti_resp.status_code == 200
        notis = noti_resp.json()["items"]
        shift_notis = [n for n in notis if n["type"] == "shift_changed"]
        assert len(shift_notis) >= 1
        assert "geändert" in shift_notis[0]["message"].lower()


# ---------------------------------------------------------------------------
# Notification service unit-ish tests
# ---------------------------------------------------------------------------
class TestNotificationService:
    def test_create_notification(self, db_session):
        _clean_notifications(db_session)
        from app.db.models.user import User
        from app.services.notification_service import create_notification

        user = db_session.query(User).first()
        n = create_notification(
            db=db_session,
            user_id=user.id,
            notification_type="wish_approved",
            title="Test Title",
            message="Test Message",
            data={"key": "value"},
        )
        assert n.id is not None
        assert n.user_id == user.id
        assert n.type == "wish_approved"
        assert n.read is False
        assert n.data["key"] == "value"

    def test_get_user_notifications(self, db_session):
        _clean_notifications(db_session)
        from app.db.models.user import User
        from app.services.notification_service import create_notification, get_user_notifications

        user = db_session.query(User).first()
        create_notification(db=db_session, user_id=user.id, notification_type="wish_approved", title="T1", message="M1")
        create_notification(db=db_session, user_id=user.id, notification_type="wish_rejected", title="T2", message="M2")

        all_notis = get_user_notifications(db=db_session, user_id=user.id)
        assert len(all_notis) == 2

        unread = get_user_notifications(db=db_session, user_id=user.id, unread_only=True)
        assert len(unread) == 2

    def test_mark_as_read_service(self, db_session):
        _clean_notifications(db_session)
        from app.db.models.user import User
        from app.services.notification_service import create_notification, mark_as_read

        user = db_session.query(User).first()
        n = create_notification(
            db=db_session, user_id=user.id, notification_type="shift_changed", title="T", message="M"
        )
        assert n.read is False

        updated = mark_as_read(db=db_session, notification_id=n.id)
        assert updated.read is True

        assert mark_as_read(db=db_session, notification_id=99999) is None

    def test_mark_all_read_service(self, db_session):
        _clean_notifications(db_session)
        from app.db.models.user import User
        from app.services.notification_service import create_notification, get_unread_count, mark_all_read

        user = db_session.query(User).first()
        for _ in range(4):
            create_notification(
                db=db_session, user_id=user.id, notification_type="wish_approved", title="T", message="M"
            )

        count = mark_all_read(db=db_session, user_id=user.id)
        assert count == 4

        assert get_unread_count(db=db_session, user_id=user.id) == 0

    def test_get_unread_count_service(self, db_session):
        _clean_notifications(db_session)
        from app.db.models.user import User
        from app.services.notification_service import create_notification, get_unread_count

        user = db_session.query(User).first()
        create_notification(db=db_session, user_id=user.id, notification_type="wish_approved", title="T", message="M")
        create_notification(db=db_session, user_id=user.id, notification_type="wish_rejected", title="T", message="M")

        assert get_unread_count(db=db_session, user_id=user.id) == 2
