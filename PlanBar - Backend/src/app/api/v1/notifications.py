from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models.notification import Notification
from app.db.models.user import User
from app.dependencies import get_current_user, get_db
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.notification_service import (
    get_unread_count,
    get_user_notifications,
    mark_all_read,
    mark_as_read,
)

router = APIRouter()


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    message: str
    read: bool
    data: dict | None = None
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/unread-count")
def get_unread_notification_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = get_unread_count(db, current_user.id)
    return {"count": count}


@router.get("", response_model=PaginatedResponse[NotificationResponse])
def list_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
):
    total_query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        total_query = total_query.filter(Notification.read == False)
    total = total_query.count()
    notifications = get_user_notifications(
        db, current_user.id, unread_only=unread_only, offset=pagination.offset, limit=pagination.limit
    )
    items = [
        {
            "id": n.id,
            "user_id": n.user_id,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "read": n.read,
            "data": n.data,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]
    return PaginatedResponse(items=items, total=total, offset=pagination.offset, limit=pagination.limit)


@router.put("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = mark_all_read(db, current_user.id)
    return {"marked": count}


@router.put("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    notification = mark_as_read(db, notification_id)
    return {
        "id": notification.id,
        "user_id": notification.user_id,
        "type": notification.type,
        "title": notification.title,
        "message": notification.message,
        "read": notification.read,
        "data": notification.data,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }
