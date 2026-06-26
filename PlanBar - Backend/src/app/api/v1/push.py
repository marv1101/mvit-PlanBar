from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.db.models.user import User
from app.services.push_service import (
    get_vapid_public_key,
    get_user_subscriptions,
    remove_subscription,
    save_subscription,
)

router = APIRouter()


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    p256dh_key: str
    auth_key: str
    device_type: str = "web"


class PushSubscriptionResponse(BaseModel):
    id: int
    endpoint: str
    device_type: str
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/vapid-public-key")
def get_vapid_public_key_endpoint():
    return {"public_key": get_vapid_public_key()}


@router.post("/subscription", status_code=status.HTTP_201_CREATED)
def create_push_subscription(
    data: PushSubscriptionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_agent = request.headers.get("user-agent", "")
    sub = save_subscription(
        db=db,
        user_id=current_user.id,
        endpoint=data.endpoint,
        p256dh_key=data.p256dh_key,
        auth_key=data.auth_key,
        device_type=data.device_type,
        user_agent=user_agent,
    )
    return {
        "id": sub.id,
        "endpoint": sub.endpoint,
        "device_type": sub.device_type,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
    }


@router.delete("/subscription", status_code=status.HTTP_204_NO_CONTENT)
def delete_push_subscription(
    endpoint: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    removed = remove_subscription(db, current_user.id, endpoint)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )


@router.get("/subscriptions")
def list_push_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscriptions = get_user_subscriptions(db, current_user.id)
    return [
        {
            "id": sub.id,
            "endpoint": sub.endpoint,
            "device_type": sub.device_type,
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
        }
        for sub in subscriptions
    ]
