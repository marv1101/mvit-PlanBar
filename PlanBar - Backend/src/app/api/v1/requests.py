from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.enums import NotificationType, WishStatus
from app.core.exceptions import NotFoundException
from app.core.versioning import ConflictError, compute_etag, detect_conflict
from app.dependencies import get_current_user, get_db, require_admin
from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.notification_service import create_notification

router = APIRouter()


class ShiftWishCreate(BaseModel):
    employee_id: int
    date: date
    week: Optional[int] = None
    type: str = Field("preferred", pattern=r"^(preferred|unavailable|vacation)$")
    note: Optional[str] = None


class ShiftWishUpdate(BaseModel):
    employee_id: Optional[int] = None
    date: Optional[date] = None
    week: Optional[int] = None
    type: Optional[str] = Field(None, pattern=r"^(preferred|unavailable|vacation)$")
    note: Optional[str] = None
    status: Optional[str] = Field(None, pattern=r"^(pending|approved|rejected)$")


class ShiftWishResponse(BaseModel):
    id: int
    employee_id: int
    date: date
    week: Optional[int] = None
    type: str
    note: Optional[str] = None
    status: str = "pending"
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    model_config = {"from_attributes": True}


class ShiftWishReject(BaseModel):
    rejection_reason: Optional[str] = None


@router.post("", response_model=ShiftWishResponse, status_code=status.HTTP_201_CREATED)
def create_shift_wish(
    data: ShiftWishCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.employee_id != data.employee_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    wish = ShiftWish(
        employee_id=data.employee_id,
        date=data.date,
        week=data.week,
        type=data.type,
        note=data.note,
        status="pending",
    )
    db.add(wish)
    db.commit()
    db.refresh(wish)
    return wish


@router.get("", response_model=PaginatedResponse[ShiftWishResponse])
def list_shift_wishes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
    status: Optional[str] = Query(None),
):
    query = db.query(ShiftWish)
    if status:
        query = query.filter(ShiftWish.status == status)
    all_wishes = query.order_by(ShiftWish.date).all()
    total = len(all_wishes)
    items = all_wishes[pagination.offset : pagination.offset + pagination.limit]
    return PaginatedResponse(items=items, total=total, offset=pagination.offset, limit=pagination.limit)


@router.get("/{wish_id}", response_model=ShiftWishResponse)
def get_shift_wish(
    wish_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wish = db.query(ShiftWish).filter(ShiftWish.id == wish_id).first()
    if not wish:
        raise NotFoundException(detail="Shift wish not found")
    return wish


@router.put("/{wish_id}", response_model=ShiftWishResponse)
def update_shift_wish(
    wish_id: int,
    data: ShiftWishUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    if_match: str | None = Header(None, alias="If-Match"),
):
    wish = db.query(ShiftWish).filter(ShiftWish.id == wish_id).first()
    if not wish:
        raise NotFoundException(detail="Shift wish not found")

    wish_etag = compute_etag({
        "date": str(wish.date),
        "type": wish.type,
        "status": wish.status,
        "updated_at": str(wish.updated_at),
    })
    try:
        detect_conflict(wish.updated_at, if_match, wish_etag)
    except ConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shift wish was modified by another user. Please refresh and try again.",
        )

    if current_user.employee_id != wish.employee_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    if data.employee_id is not None:
        wish.employee_id = data.employee_id
    if data.date is not None:
        wish.date = data.date
    if data.week is not None:
        wish.week = data.week
    if data.type is not None:
        wish.type = data.type
    if data.note is not None:
        wish.note = data.note
    if data.status is not None:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can update wish status",
            )
        wish.status = data.status
    db.add(wish)
    db.commit()
    db.refresh(wish)
    return wish


@router.delete("/{wish_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shift_wish(
    wish_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wish = db.query(ShiftWish).filter(ShiftWish.id == wish_id).first()
    if not wish:
        raise NotFoundException(detail="Shift wish not found")
    if current_user.employee_id != wish.employee_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    db.delete(wish)
    db.commit()


@router.put("/{wish_id}/approve", response_model=ShiftWishResponse)
def approve_shift_wish(
    wish_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    wish = db.query(ShiftWish).filter(ShiftWish.id == wish_id).first()
    if not wish:
        raise NotFoundException(detail="Shift wish not found")
    wish.status = WishStatus.APPROVED.value
    wish.reviewed_by = admin.id
    wish.reviewed_at = datetime.now()
    wish.rejection_reason = None
    db.add(wish)
    db.commit()
    db.refresh(wish)

    # Create notification for the employee's linked user
    from app.db.models.employee import Employee

    employee = db.query(Employee).filter(Employee.id == wish.employee_id).first()
    if employee and employee.user_id:
        create_notification(
            db=db,
            user_id=employee.user_id,
            notification_type=NotificationType.WISH_APPROVED.value,
            title="Wunsch genehmigt",
            message=f"Dein Schichtwunsch für {wish.date} wurde genehmigt.",
            data={"wish_id": wish.id, "date": str(wish.date), "type": wish.type},
        )

    return wish


@router.put("/{wish_id}/reject", response_model=ShiftWishResponse)
def reject_shift_wish(
    wish_id: int,
    body: ShiftWishReject,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    wish = db.query(ShiftWish).filter(ShiftWish.id == wish_id).first()
    if not wish:
        raise NotFoundException(detail="Shift wish not found")
    wish.status = WishStatus.REJECTED.value
    wish.reviewed_by = admin.id
    wish.reviewed_at = datetime.now()
    wish.rejection_reason = body.rejection_reason
    db.add(wish)
    db.commit()
    db.refresh(wish)

    # Create notification for the employee's linked user
    from app.db.models.employee import Employee

    employee = db.query(Employee).filter(Employee.id == wish.employee_id).first()
    if employee and employee.user_id:
        reason_text = f" Grund: {body.rejection_reason}" if body.rejection_reason else ""
        create_notification(
            db=db,
            user_id=employee.user_id,
            notification_type=NotificationType.WISH_REJECTED.value,
            title="Wunsch abgelehnt",
            message=f"Dein Schichtwunsch für {wish.date} wurde abgelehnt.{reason_text}",
            data={
                "wish_id": wish.id,
                "date": str(wish.date),
                "type": wish.type,
                "rejection_reason": body.rejection_reason,
            },
        )

    return wish
