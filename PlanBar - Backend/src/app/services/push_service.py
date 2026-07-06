import json
import logging
from pathlib import Path

from py_vapid import Vapid
from pywebpush import webpush, WebPushException
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)

VAPID_KEY_FILE = Path("vapid_keys.json")

_vapid_private_key: str | None = None
_vapid_public_key: str | None = None


def _load_or_generate_vapid_keys() -> tuple[str, str]:
    global _vapid_private_key, _vapid_public_key
    if _vapid_private_key and _vapid_public_key:
        return _vapid_private_key, _vapid_public_key
    private_key = settings.vapid_private_key
    public_key = settings.vapid_public_key
    if private_key and public_key:
        _vapid_private_key = private_key
        _vapid_public_key = public_key
        return _vapid_private_key, _vapid_public_key
    if VAPID_KEY_FILE.exists():
        try:
            data = json.loads(VAPID_KEY_FILE.read_text())
            _vapid_private_key = data["private_key"]
            _vapid_public_key = data["public_key"]
            return _vapid_private_key, _vapid_public_key
        except Exception:
            logger.warning("Failed to load VAPID keys from file, generating new ones")
    vapid = Vapid()
    vapid.generate_keys()
    _vapid_private_key = vapid.private_pem().decode("utf-8")
    _vapid_public_key = vapid.public_pem().decode("utf-8")
    try:
        VAPID_KEY_FILE.write_text(json.dumps({"private_key": _vapid_private_key, "public_key": _vapid_public_key}))
    except Exception as e:
        logger.warning("Could not persist VAPID keys to file: %s", e)
    return _vapid_private_key, _vapid_public_key


def get_vapid_public_key() -> str:
    _, public_key = _load_or_generate_vapid_keys()
    return public_key


def _get_vapid_claims() -> dict[str, str]:
    private_key, _ = _load_or_generate_vapid_keys()
    return {
        "sub": settings.vapid_claim_email,
        "aud": "https://fcm.googleapis.com",
        "private_key": private_key,
    }


def save_subscription(
    db: Session,
    user_id: int,
    endpoint: str,
    p256dh_key: str,
    auth_key: str,
    device_type: str = "web",
    user_agent: str | None = None,
) -> PushSubscription:
    existing = (
        db.query(PushSubscription)
        .filter(
            PushSubscription.user_id == user_id,
            PushSubscription.endpoint == endpoint,
        )
        .first()
    )
    if existing:
        existing.p256dh_key = p256dh_key
        existing.auth_key = auth_key
        existing.device_type = device_type
        existing.user_agent = user_agent
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    sub = PushSubscription(
        user_id=user_id,
        endpoint=endpoint,
        p256dh_key=p256dh_key,
        auth_key=auth_key,
        device_type=device_type,
        user_agent=user_agent,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def remove_subscription(db: Session, user_id: int, endpoint: str) -> bool:
    sub = (
        db.query(PushSubscription)
        .filter(
            PushSubscription.user_id == user_id,
            PushSubscription.endpoint == endpoint,
        )
        .first()
    )
    if not sub:
        return False
    db.delete(sub)
    db.commit()
    return True


def get_user_subscriptions(db: Session, user_id: int) -> list[PushSubscription]:
    return db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all()


def send_push_notification(
    subscription: PushSubscription,
    title: str,
    body: str,
    url: str | None = None,
    tag: str | None = None,
) -> bool:
    vapid_claims = _get_vapid_claims()
    payload = {
        "title": title,
        "body": body,
    }
    if url:
        payload["url"] = url
    if tag:
        payload["tag"] = tag
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh_key,
                    "auth": subscription.auth_key,
                },
            },
            data=json.dumps(payload),
            vapid_private_key=vapid_claims["private_key"],
            vapid_claims={
                "sub": vapid_claims["sub"],
            },
        )
        return True
    except WebPushException as e:
        if e.response and e.response.status_code in (410, 404):
            logger.info("Push subscription expired or gone, will be cleaned up later")
        else:
            logger.warning("Push notification failed: %s", e)
        return False


def send_push_notification_to_user(
    db: Session,
    user_id: int,
    title: str,
    body: str,
    url: str | None = None,
    tag: str | None = None,
) -> int:
    subscriptions = get_user_subscriptions(db, user_id)
    sent_count = 0
    for sub in subscriptions:
        success = send_push_notification(sub, title, body, url, tag)
        if success:
            sent_count += 1
        else:
            if sub.endpoint:
                db.delete(sub)
    if subscriptions:
        db.commit()
    return sent_count
