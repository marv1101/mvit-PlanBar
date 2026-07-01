"""Unit tests for the webhook service."""

import json
import hashlib
import hmac
from unittest.mock import patch, MagicMock

import pytest

from app.db.models.webhook import Webhook, WebhookLog
from app.services.webhook_service import (
    MAX_LOGS_PER_WEBHOOK,
    MAX_RETRIES,
    _compute_signature,
    _deliver_webhook,
    _log_attempt,
    create_webhook,
    delete_webhook,
    get_webhook_logs,
    regenerate_secret,
    update_webhook,
)


class TestWebhookCRUD:
    def test_create_webhook(self, db_session):
        wh = create_webhook(db_session, url="https://example.com/hook", events=["test.event"])
        assert wh.id is not None
        assert wh.url == "https://example.com/hook"
        assert wh.events == ["test.event"]
        assert wh.secret is not None
        assert len(wh.secret) == 64
        assert wh.active is True

    def test_create_webhook_with_custom_secret(self, db_session):
        wh = create_webhook(
            db_session,
            url="https://example.com/hook",
            events=["test.event"],
            secret="my-custom-secret",
        )
        assert wh.secret == "my-custom-secret"

    def test_update_webhook_url_and_events(self, db_session):
        wh = create_webhook(db_session, url="https://example.com/hook", events=["test.event"])
        updated = update_webhook(
            db_session, wh.id, url="https://new-url.com", events=["event.a", "event.b"]
        )
        assert updated is not None
        assert updated.url == "https://new-url.com"
        assert updated.events == ["event.a", "event.b"]
        assert updated.active is True

    def test_update_webhook_active(self, db_session):
        wh = create_webhook(db_session, url="https://example.com/hook", events=["test.event"])
        updated = update_webhook(db_session, wh.id, active=False)
        assert updated is not None
        assert updated.active is False

    def test_update_webhook_not_found(self, db_session):
        result = update_webhook(db_session, 99999, active=False)
        assert result is None

    def test_delete_webhook(self, db_session):
        wh = create_webhook(db_session, url="https://example.com/hook", events=["test.event"])
        assert delete_webhook(db_session, wh.id) is True
        assert db_session.query(Webhook).filter(Webhook.id == wh.id).first() is None

    def test_delete_webhook_not_found(self, db_session):
        assert delete_webhook(db_session, 99999) is False

    def test_regenerate_secret(self, db_session):
        wh = create_webhook(db_session, url="https://example.com/hook", events=["test.event"])
        old_secret = wh.secret
        updated = regenerate_secret(db_session, wh.id)
        assert updated is not None
        assert updated.secret != old_secret
        assert len(updated.secret) == 64

    def test_regenerate_secret_not_found(self, db_session):
        assert regenerate_secret(db_session, 99999) is None

    def test_get_webhook_logs_empty(self, db_session):
        wh = create_webhook(db_session, url="https://example.com/hook", events=["test.event"])
        logs = get_webhook_logs(db_session, wh.id)
        assert logs == []


class TestWebhookSignature:
    def test_compute_signature(self):
        secret = "test-secret"
        payload = b'{"event": "test", "data": {}}'
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert _compute_signature(secret, payload) == expected

    def test_signature_differs_with_different_secret(self):
        payload = b'{"event": "test"}'
        sig1 = _compute_signature("secret1", payload)
        sig2 = _compute_signature("secret2", payload)
        assert sig1 != sig2


class TestWebhookDelivery:
    def test_log_attempt_creates_entry(self, db_session):
        wh = create_webhook(db_session, url="https://example.com/hook", events=["test.event"])
        payload = json.dumps({"event": "test.event", "data": {}}).encode()
        _log_attempt(
            webhook_id=wh.id,
            event="test.event",
            url="https://example.com/hook",
            payload=payload,
            response_status=200,
            error_message=None,
            attempt=1,
            success=True,
            db=db_session,
        )
        logs = db_session.query(WebhookLog).filter(WebhookLog.webhook_id == wh.id).all()
        assert len(logs) == 1
        assert logs[0].success is True
        assert logs[0].attempt == 1
        assert logs[0].response_status == 200
        assert logs[0].event == "test.event"

    def test_log_attempt_dead_letter(self, db_session):
        wh = create_webhook(db_session, url="https://example.com/hook", events=["test.event"])
        payload = json.dumps({"event": "test.event", "data": {}}).encode()
        _log_attempt(
            webhook_id=wh.id,
            event="test.event",
            url="https://example.com/hook",
            payload=payload,
            response_status=None,
            error_message="Connection refused",
            attempt=3,
            success=False,
            dead_letter=True,
            db=db_session,
        )
        logs = db_session.query(WebhookLog).filter(WebhookLog.webhook_id == wh.id).all()
        assert len(logs) == 1
        assert logs[0].success is False
        assert logs[0].dead_letter is True
        assert logs[0].error_message == "Connection refused"

    def test_log_attempt_trim_old_entries(self, db_session):
        wh = create_webhook(db_session, url="https://example.com/hook", events=["test.event"])
        # Create MAX_LOGS_PER_WEBHOOK log entries
        for i in range(MAX_LOGS_PER_WEBHOOK):
            log_entry = WebhookLog(
                webhook_id=wh.id,
                event="test.event",
                request_url="https://example.com/hook",
                request_body="{}",
                response_status=200,
                success=True,
                attempt=1,
            )
            db_session.add(log_entry)
        db_session.commit()

        assert db_session.query(WebhookLog).filter(WebhookLog.webhook_id == wh.id).count() == MAX_LOGS_PER_WEBHOOK

        # Add one more - oldest should be removed
        _log_attempt(
            webhook_id=wh.id,
            event="test.event",
            url="https://example.com/hook",
            payload=b"{}",
            response_status=200,
            error_message=None,
            attempt=1,
            success=True,
            db=db_session,
        )
        assert db_session.query(WebhookLog).filter(WebhookLog.webhook_id == wh.id).count() == MAX_LOGS_PER_WEBHOOK

    @patch("app.services.webhook_service.httpx.post")
    def test_deliver_webhook_success(self, mock_post, db_session):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        wh = create_webhook(db_session, url="https://example.com/hook", events=["test.event"])

        _deliver_webhook(wh, "test.event", {"key": "value"}, db=db_session)

        mock_post.assert_called_once()
        call_args, call_kwargs = mock_post.call_args
        assert call_args[0] == "https://example.com/hook"
        assert call_kwargs["headers"]["X-Webhook-Event"] == "test.event"
        assert "X-Webhook-Signature" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Content-Type"] == "application/json"

        # Verify log was created
        logs = db_session.query(WebhookLog).filter(WebhookLog.webhook_id == wh.id).all()
        assert len(logs) == 1
        assert logs[0].success is True
        assert logs[0].response_status == 200

    @patch("app.services.webhook_service.httpx.post")
    def test_deliver_webhook_retry_on_failure(self, mock_post, db_session):
        mock_post.side_effect = ConnectionError("Connection refused")

        wh = create_webhook(db_session, url="https://example.com/hook", events=["test.event"])

        _deliver_webhook(wh, "test.event", {"key": "value"}, db=db_session)

        # Should have retried MAX_RETRIES times
        assert mock_post.call_count == MAX_RETRIES

        logs = db_session.query(WebhookLog).filter(WebhookLog.webhook_id == wh.id).all()
        assert len(logs) == MAX_RETRIES

    @patch("app.services.webhook_service.httpx.post")
    def test_deliver_webhook_signature_header(self, mock_post, db_session):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        wh = create_webhook(
            db_session,
            url="https://example.com/hook",
            events=["test.event"],
            secret="known-secret",
        )

        _deliver_webhook(wh, "test.event", {"msg": "hello"}, db=db_session)

        _, call_kwargs = mock_post.call_args
        signature = call_kwargs["headers"]["X-Webhook-Signature"]
        payload = call_kwargs["content"]

        expected = hmac.new(b"known-secret", payload, hashlib.sha256).hexdigest()
        assert signature == expected
