import hashlib
import hmac
import json
import logging
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.event_bus import event_bus
from app.db.database import SessionLocal
from app.db.models.webhook import Webhook, WebhookLog

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
MAX_LOGS_PER_WEBHOOK = 100


def _compute_signature(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _log_attempt(
    webhook_id: int,
    event: str,
    url: str,
    payload: bytes | None,
    response_status: int | None,
    error_message: str | None,
    attempt: int,
    success: bool,
    dead_letter: bool = False,
    db: Session | None = None,
) -> None:
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        count = db.query(WebhookLog).filter(WebhookLog.webhook_id == webhook_id).count()
        if count >= MAX_LOGS_PER_WEBHOOK:
            oldest = (
                db.query(WebhookLog)
                .filter(WebhookLog.webhook_id == webhook_id)
                .order_by(WebhookLog.created_at.asc())
                .first()
            )
            if oldest:
                db.delete(oldest)

        log_entry = WebhookLog(
            webhook_id=webhook_id,
            event=event,
            request_url=url,
            request_body=payload.decode("utf-8") if payload else None,
            response_status=response_status,
            response_body=error_message if error_message else None,
            success=success,
            error_message=error_message,
            attempt=attempt,
            dead_letter=dead_letter,
        )
        db.add(log_entry)
        db.commit()
    except Exception:
        logger.exception("Failed to log webhook delivery attempt")
    finally:
        if close_db:
            db.close()


def _deliver_webhook(
    webhook: Webhook,
    event: str,
    data: dict[str, Any],
    db: Session | None = None,
) -> None:
    url = webhook.url
    secret = webhook.secret
    payload_dict = {
        "event": event,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    signature = _compute_signature(secret, payload_bytes)

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": event,
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = httpx.post(url, content=payload_bytes, headers=headers, timeout=10.0)
            _log_attempt(
                webhook.id,
                event,
                url,
                payload_bytes,
                response.status_code,
                None,
                attempt,
                True,
                db=db,
            )
            logger.info("Webhook delivered to %s (event=%s, status=%d)", url, event, response.status_code)
            return
        except Exception as e:
            last_error = str(e)
            logger.warning(
                "Webhook attempt %d/%d failed for %s: %s",
                attempt,
                MAX_RETRIES,
                url,
                last_error,
            )
            _log_attempt(
                webhook.id,
                event,
                url,
                payload_bytes,
                None,
                last_error,
                attempt,
                False,
                dead_letter=(attempt == MAX_RETRIES),
                db=db,
            )
            if attempt < MAX_RETRIES:
                time.sleep(2**attempt)

    logger.error("Webhook dead-lettered for %s (event=%s): %s", url, event, last_error)


def _handle_event(event: str, data: dict[str, Any]) -> None:
    db = SessionLocal()
    try:
        webhooks = db.query(Webhook).filter(Webhook.active == True).all()
        for webhook in webhooks:
            if event in webhook.events:
                threading.Thread(
                    target=_deliver_webhook,
                    args=(webhook, event, data),
                    daemon=True,
                ).start()
    except Exception:
        logger.exception("Error handling webhook event")
    finally:
        db.close()


def init_event_subscriptions() -> None:
    event_bus.subscribe("*", _handle_event)
    logger.info("Webhook event subscriptions initialized")


def create_webhook(
    db: Session,
    url: str,
    events: list[str],
    secret: str | None = None,
) -> Webhook:
    webhook = Webhook(
        url=url,
        events=events,
        secret=secret or secrets.token_hex(32),
        active=True,
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


def update_webhook(
    db: Session,
    webhook_id: int,
    url: str | None = None,
    events: list[str] | None = None,
    active: bool | None = None,
) -> Webhook | None:
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        return None
    if url is not None:
        webhook.url = url
    if events is not None:
        webhook.events = events
    if active is not None:
        webhook.active = active
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


def regenerate_secret(db: Session, webhook_id: int) -> Webhook | None:
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        return None
    webhook.secret = secrets.token_hex(32)
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


def delete_webhook(db: Session, webhook_id: int) -> bool:
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        return False
    db.delete(webhook)
    db.commit()
    return True


def get_webhook_logs(
    db: Session,
    webhook_id: int,
    limit: int = 100,
) -> list[WebhookLog]:
    return (
        db.query(WebhookLog)
        .filter(WebhookLog.webhook_id == webhook_id)
        .order_by(WebhookLog.created_at.desc())
        .limit(limit)
        .all()
    )


def send_test_event(db: Session, webhook_id: int) -> bool:
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        return False
    threading.Thread(
        target=_deliver_webhook,
        args=(
            webhook,
            "test.ping",
            {"message": "Dies ist ein Test-Webhook von PlanBar."},
        ),
        daemon=True,
    ).start()
    return True
