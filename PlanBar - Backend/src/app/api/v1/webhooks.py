from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.dependencies import get_db, require_admin
from app.db.models.user import User
from app.db.models.webhook import Webhook
from app.schemas.webhook import (
    TestEventResponse,
    WebhookCreate,
    WebhookDetailResponse,
    WebhookLogResponse,
    WebhookResponse,
    WebhookSecretResponse,
    WebhookUpdate,
)
from app.services import webhook_service

router = APIRouter()


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    data: WebhookCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    wh = webhook_service.create_webhook(db, url=data.url, events=data.events)
    return _webhook_to_response(wh)


@router.get("", response_model=list[WebhookResponse])
def list_webhooks(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    webhooks = db.query(Webhook).order_by(Webhook.created_at.desc()).all()
    return [_webhook_to_response(wh) for wh in webhooks]


@router.get("/{webhook_id}", response_model=WebhookDetailResponse)
def get_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    wh = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not wh:
        raise NotFoundException(detail="Webhook not found")
    return _webhook_to_detail_response(wh)


@router.put("/{webhook_id}", response_model=WebhookResponse)
def update_webhook(
    webhook_id: int,
    data: WebhookUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    wh = webhook_service.update_webhook(
        db, webhook_id, url=data.url, events=data.events, active=data.active
    )
    if not wh:
        raise NotFoundException(detail="Webhook not found")
    return _webhook_to_response(wh)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if not webhook_service.delete_webhook(db, webhook_id):
        raise NotFoundException(detail="Webhook not found")


@router.post("/{webhook_id}/regenerate-secret", response_model=WebhookSecretResponse)
def regenerate_webhook_secret(
    webhook_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    wh = webhook_service.regenerate_secret(db, webhook_id)
    if not wh:
        raise NotFoundException(detail="Webhook not found")
    return WebhookSecretResponse(
        id=wh.id,
        url=wh.url,
        secret=wh.secret,
        events=wh.events,
        active=wh.active,
    )


@router.get("/{webhook_id}/logs", response_model=list[WebhookLogResponse])
def get_webhook_logs(
    webhook_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    wh = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not wh:
        raise NotFoundException(detail="Webhook not found")
    logs = webhook_service.get_webhook_logs(db, webhook_id)
    return [
        WebhookLogResponse(
            id=log.id,
            webhook_id=log.webhook_id,
            event=log.event,
            request_url=log.request_url,
            request_body=log.request_body,
            response_status=log.response_status,
            response_body=log.response_body,
            success=log.success,
            error_message=log.error_message,
            attempt=log.attempt,
            dead_letter=log.dead_letter,
            created_at=log.created_at.isoformat() if log.created_at else None,
        )
        for log in logs
    ]


@router.post("/{webhook_id}/test", response_model=TestEventResponse)
def send_test_event(
    webhook_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if not webhook_service.send_test_event(db, webhook_id):
        raise NotFoundException(detail="Webhook not found")
    return TestEventResponse(status="test_event_sent")


def _webhook_to_response(wh: Webhook) -> WebhookResponse:
    return WebhookResponse(
        id=wh.id,
        url=wh.url,
        events=wh.events,
        active=wh.active,
        created_at=wh.created_at.isoformat() if wh.created_at else None,
        updated_at=wh.updated_at.isoformat() if wh.updated_at else None,
    )


def _webhook_to_detail_response(wh: Webhook) -> WebhookDetailResponse:
    return WebhookDetailResponse(
        id=wh.id,
        url=wh.url,
        events=wh.events,
        secret=wh.secret,
        active=wh.active,
        created_at=wh.created_at.isoformat() if wh.created_at else None,
        updated_at=wh.updated_at.isoformat() if wh.updated_at else None,
    )
