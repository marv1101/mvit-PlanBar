"""Integration tests for push notification subscription endpoints."""


def _clean_push_subscriptions(db_session):
    from app.db.models.push_subscription import PushSubscription

    db_session.query(PushSubscription).delete()
    db_session.commit()


class TestVapidPublicKey:
    """Tests for GET /push/vapid-public-key."""

    def test_get_vapid_public_key(self, client, auth_headers):
        resp = client.get("/api/v1/push/vapid-public-key", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "public_key" in data
        assert len(data["public_key"]) > 0

    def test_public_key_accessible_without_auth(self, client):
        resp = client.get("/api/v1/push/vapid-public-key")
        assert resp.status_code == 200
        assert "public_key" in resp.json()


class TestPushSubscription:
    """Tests for POST/DELETE /push/subscription."""

    def test_create_subscription(self, client, auth_headers, db_session):
        _clean_push_subscriptions(db_session)
        resp = client.post(
            "/api/v1/push/subscription",
            json={
                "endpoint": "https://example.com/push/endpoint1",
                "p256dh_key": "test_p256dh_key_123",
                "auth_key": "test_auth_key_456",
                "device_type": "web",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["endpoint"] == "https://example.com/push/endpoint1"
        assert data["device_type"] == "web"
        assert "id" in data

    def test_create_subscription_updates_existing(self, client, auth_headers, db_session):
        _clean_push_subscriptions(db_session)
        resp1 = client.post(
            "/api/v1/push/subscription",
            json={
                "endpoint": "https://example.com/push/endpoint2",
                "p256dh_key": "old_key",
                "auth_key": "old_auth",
            },
            headers=auth_headers,
        )
        assert resp1.status_code == 201
        sub_id = resp1.json()["id"]

        resp2 = client.post(
            "/api/v1/push/subscription",
            json={
                "endpoint": "https://example.com/push/endpoint2",
                "p256dh_key": "new_key",
                "auth_key": "new_auth",
            },
            headers=auth_headers,
        )
        assert resp2.status_code == 201
        assert resp2.json()["id"] == sub_id

    def test_delete_subscription(self, client, auth_headers, db_session):
        _clean_push_subscriptions(db_session)
        client.post(
            "/api/v1/push/subscription",
            json={
                "endpoint": "https://example.com/push/delete_me",
                "p256dh_key": "key",
                "auth_key": "auth",
            },
            headers=auth_headers,
        )

        resp = client.delete(
            "/api/v1/push/subscription",
            params={"endpoint": "https://example.com/push/delete_me"},
            headers=auth_headers,
        )
        assert resp.status_code == 204

    def test_delete_nonexistent_subscription(self, client, auth_headers):
        resp = client.delete(
            "/api/v1/push/subscription",
            params={"endpoint": "https://example.com/push/nonexistent"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_list_subscriptions(self, client, auth_headers, db_session):
        _clean_push_subscriptions(db_session)
        client.post(
            "/api/v1/push/subscription",
            json={
                "endpoint": "https://example.com/push/list1",
                "p256dh_key": "key1",
                "auth_key": "auth1",
            },
            headers=auth_headers,
        )
        client.post(
            "/api/v1/push/subscription",
            json={
                "endpoint": "https://example.com/push/list2",
                "p256dh_key": "key2",
                "auth_key": "auth2",
            },
            headers=auth_headers,
        )

        resp = client.get("/api/v1/push/subscriptions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_subscriptions_isolated_per_user(self, client, auth_headers, employee_auth_headers, db_session):
        _clean_push_subscriptions(db_session)
        emp_headers = employee_auth_headers[0] if isinstance(employee_auth_headers, tuple) else employee_auth_headers

        client.post(
            "/api/v1/push/subscription",
            json={
                "endpoint": "https://example.com/push/admin_only",
                "p256dh_key": "k",
                "auth_key": "a",
            },
            headers=auth_headers,
        )

        resp = client.get("/api/v1/push/subscriptions", headers=emp_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_requires_auth(self, client):
        resp = client.post(
            "/api/v1/push/subscription",
            json={"endpoint": "e", "p256dh_key": "k", "auth_key": "a"},
        )
        assert resp.status_code == 401

        resp = client.delete("/api/v1/push/subscription", params={"endpoint": "e"})
        assert resp.status_code == 401


class TestPushService:
    """Tests for push service functions."""

    def test_save_and_remove_subscription(self, db_session):
        from app.db.models.user import User
        from app.services.push_service import save_subscription, remove_subscription, get_user_subscriptions

        user = db_session.query(User).first()

        sub = save_subscription(
            db=db_session,
            user_id=user.id,
            endpoint="https://test/svc_endpoint",
            p256dh_key="p256",
            auth_key="auth",
            device_type="mobile",
        )
        assert sub.id is not None
        assert sub.device_type == "mobile"

        subs = get_user_subscriptions(db=db_session, user_id=user.id)
        assert len(subs) == 1

        removed = remove_subscription(db=db_session, user_id=user.id, endpoint="https://test/svc_endpoint")
        assert removed is True

        removed = remove_subscription(db=db_session, user_id=user.id, endpoint="https://test/svc_endpoint")
        assert removed is False

        subs = get_user_subscriptions(db=db_session, user_id=user.id)
        assert len(subs) == 0

    def test_get_vapid_public_key_service(self):
        from app.services.push_service import get_vapid_public_key

        key = get_vapid_public_key()
        assert key.startswith("-----BEGIN PUBLIC KEY-----")
