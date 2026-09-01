"""Integration tests for the Webhook API endpoints."""

import json
from unittest.mock import MagicMock, patch

from app.core.event_bus import EventBus


def _clean_webhooks(db_session):
    from app.core.event_bus import EventBus

    EventBus()._subscribers.clear()
    from app.db.models.webhook import Webhook, WebhookLog

    db_session.query(WebhookLog).delete()
    db_session.query(Webhook).delete()
    db_session.commit()


WEBHOOK_EVENTS = [
    "schedule.created",
    "schedule.published",
    "shift.assigned",
    "shift.swapped",
    "shift.modified",
    "employee.created",
    "employee.updated",
    "leave.requested",
    "leave.approved",
    "leave.rejected",
]


class TestWebhookAdminEndpoints:
    """Tests for admin webhook CRUD endpoints."""

    def test_create_webhook(self, client, auth_headers, db_session):
        _clean_webhooks(db_session)
        resp = client.post(
            "/api/v1/admin/webhooks",
            json={"url": "https://example.com/hook", "events": ["test.event"]},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["url"] == "https://example.com/hook"
        assert data["events"] == ["test.event"]
        assert data["active"] is True
        assert "secret" not in data  # secret should not be in list response
        assert "id" in data

    def test_create_webhook_validates_url(self, client, auth_headers, db_session):
        _clean_webhooks(db_session)
        resp = client.post(
            "/api/v1/admin/webhooks",
            json={"url": "not-a-url", "events": ["test.event"]},
            headers=auth_headers,
        )
        assert resp.status_code == 422, resp.text

    def test_list_webhooks(self, client, auth_headers, db_session):
        _clean_webhooks(db_session)
        client.post(
            "/api/v1/admin/webhooks",
            json={"url": "https://example.com/hook1", "events": ["event.a"]},
            headers=auth_headers,
        )
        client.post(
            "/api/v1/admin/webhooks",
            json={"url": "https://example.com/hook2", "events": ["event.b"]},
            headers=auth_headers,
        )

        resp = client.get("/api/v1/admin/webhooks", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["url"] in ("https://example.com/hook1", "https://example.com/hook2")

    def test_get_webhook(self, client, auth_headers, db_session):
        _clean_webhooks(db_session)
        create_resp = client.post(
            "/api/v1/admin/webhooks",
            json={"url": "https://example.com/hook", "events": ["test.event"]},
            headers=auth_headers,
        )
        wh_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/admin/webhooks/{wh_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "https://example.com/hook"
        assert data["events"] == ["test.event"]
        assert "secret" in data  # single webhook view should include secret

    def test_get_webhook_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/admin/webhooks/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_webhook(self, client, auth_headers, db_session):
        _clean_webhooks(db_session)
        create_resp = client.post(
            "/api/v1/admin/webhooks",
            json={"url": "https://example.com/hook", "events": ["test.event"]},
            headers=auth_headers,
        )
        wh_id = create_resp.json()["id"]

        resp = client.put(
            f"/api/v1/admin/webhooks/{wh_id}",
            json={"url": "https://new-url.com", "events": ["event.a", "event.b"], "active": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "https://new-url.com"
        assert data["events"] == ["event.a", "event.b"]
        assert data["active"] is False

    def test_update_webhook_partial(self, client, auth_headers, db_session):
        _clean_webhooks(db_session)
        create_resp = client.post(
            "/api/v1/admin/webhooks",
            json={"url": "https://example.com/hook", "events": ["test.event"]},
            headers=auth_headers,
        )
        wh_id = create_resp.json()["id"]

        resp = client.put(
            f"/api/v1/admin/webhooks/{wh_id}",
            json={"active": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["active"] is False
        assert data["url"] == "https://example.com/hook"  # unchanged

    def test_delete_webhook(self, client, auth_headers, db_session):
        _clean_webhooks(db_session)
        create_resp = client.post(
            "/api/v1/admin/webhooks",
            json={"url": "https://example.com/hook", "events": ["test.event"]},
            headers=auth_headers,
        )
        wh_id = create_resp.json()["id"]

        resp = client.delete(f"/api/v1/admin/webhooks/{wh_id}", headers=auth_headers)
        assert resp.status_code == 204

        # Verify it's gone
        get_resp = client.get(f"/api/v1/admin/webhooks/{wh_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_webhooks_endpoint_requires_admin(self, client, employee_auth_headers):
        emp_headers, _ = employee_auth_headers
        resp = client.get("/api/v1/admin/webhooks", headers=emp_headers)
        assert resp.status_code == 403

    def test_create_webhook_requires_admin(self, client, employee_auth_headers):
        emp_headers, _ = employee_auth_headers
        resp = client.post(
            "/api/v1/admin/webhooks",
            json={"url": "https://example.com/hook", "events": ["test.event"]},
            headers=emp_headers,
        )
        assert resp.status_code == 403


class TestWebhookSecret:
    def test_regenerate_secret(self, client, auth_headers, db_session):
        _clean_webhooks(db_session)
        create_resp = client.post(
            "/api/v1/admin/webhooks",
            json={"url": "https://example.com/hook", "events": ["test.event"]},
            headers=auth_headers,
        )
        wh_id = create_resp.json()["id"]

        resp = client.post(f"/api/v1/admin/webhooks/{wh_id}/regenerate-secret", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "secret" in data
        assert len(data["secret"]) == 64

        # Verify the secret actually changed
        get_resp = client.get(f"/api/v1/admin/webhooks/{wh_id}", headers=auth_headers)
        assert get_resp.json()["secret"] == data["secret"]


class TestWebhookLogs:
    def test_get_webhook_logs(self, client, auth_headers, db_session):
        _clean_webhooks(db_session)
        create_resp = client.post(
            "/api/v1/admin/webhooks",
            json={"url": "https://example.com/hook", "events": ["test.event"]},
            headers=auth_headers,
        )
        wh_id = create_resp.json()["id"]

        # Create a log entry directly
        from app.db.models.webhook import WebhookLog

        log_entry = WebhookLog(
            webhook_id=wh_id,
            event="test.event",
            request_url="https://example.com/hook",
            request_body='{"event":"test.event","data":{}}',
            response_status=200,
            success=True,
            attempt=1,
        )
        db_session.add(log_entry)
        db_session.commit()

        resp = client.get(f"/api/v1/admin/webhooks/{wh_id}/logs", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["event"] == "test.event"
        assert data[0]["success"] is True


class TestWebhookTestEvent:
    @patch("app.services.webhook_service.httpx.post")
    def test_send_test_event(self, mock_post, client, auth_headers, db_session):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        _clean_webhooks(db_session)
        create_resp = client.post(
            "/api/v1/admin/webhooks",
            json={"url": "https://example.com/hook", "events": ["test.event"]},
            headers=auth_headers,
        )
        wh_id = create_resp.json()["id"]

        resp = client.post(f"/api/v1/admin/webhooks/{wh_id}/test", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "test_event_sent"

        # Wait for the background thread
        import time

        time.sleep(0.1)

        # Verify the webhook was called with test.ping event
        assert mock_post.called
        _, call_kwargs = mock_post.call_args
        assert call_kwargs["headers"]["X-Webhook-Event"] == "test.ping"
        payload = json.loads(call_kwargs["content"])
        assert payload["event"] == "test.ping"
        assert "message" in payload["data"]

    def test_send_test_event_not_found(self, client, auth_headers):
        resp = client.post("/api/v1/admin/webhooks/99999/test", headers=auth_headers)
        assert resp.status_code == 404


class TestWebhookEventFiring:
    def test_employee_created_fires_event(self, client, auth_headers, db_session):
        _clean_webhooks(db_session)

        events = []

        def listener(etype, data):
            events.append((etype, data))

        bus = EventBus()
        bus.subscribe("employee.created", listener)

        resp = client.post(
            "/api/v1/employees",
            json={"first_name": "Webhook", "last_name": "Test"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

        assert len(events) >= 1
        assert events[0][0] == "employee.created"
        assert events[0][1]["employee_id"] == resp.json()["id"]

    def test_schedule_created_fires_event(self, client, auth_headers, db_session):
        _clean_webhooks(db_session)

        events = []

        def listener(etype, data):
            events.append((etype, data))

        bus = EventBus()
        bus.subscribe("schedule.created", listener)

        resp = client.post(
            "/api/v1/schedules",
            json={
                "name": "Webhook Schedule",
                "start_date": "2026-08-01",
                "end_date": "2026-08-07",
                "role_requirements": {"früh": "1"},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201

        assert len(events) >= 1
        assert events[0][0] == "schedule.created"
        assert events[0][1]["schedule_id"] == resp.json()["id"]


class TestWebhookUnauthenticated:
    def test_webhooks_requires_auth(self, client):
        resp = client.get("/api/v1/admin/webhooks")
        assert resp.status_code == 401

    def test_create_webhook_requires_auth(self, client):
        resp = client.post(
            "/api/v1/admin/webhooks",
            json={"url": "https://example.com/hook", "events": ["test.event"]},
        )
        assert resp.status_code == 401
