from datetime import UTC, datetime
from datetime import date as Date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.enums import NotificationType, WishStatus
from app.core.exceptions import NotFoundException
from app.core.versioning import ConflictError, check_etag_conflict, set_etag_header, set_etag_response
from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User
from app.dependencies import get_current_user, get_db, require_admin_or_planer
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services import team_service
from app.services.notification_service import create_notification_and_push
from app.services.schedule_service import wish_week_for_date

router = APIRouter()


class ShiftWishCreate(BaseModel):
    employee_id: int
    date: Date
    week: int | None = None
    type: str = Field("preferred", pattern=r"^(preferred|unavailable|vacation)$")
    note: str | None = None


class ShiftWishUpdate(BaseModel):
    employee_id: int | None = None
    date: Date | None = None
    week: int | None = None
    type: str | None = Field(None, pattern=r"^(preferred|unavailable|vacation)$")
    note: str | None = None
    status: str | None = Field(None, pattern=r"^(pending|approved|rejected)$")


class ShiftWishResponse(BaseModel):
    id: int
    employee_id: int
    date: Date
    week: int | None = None
    type: str
    note: str | None = None
    status: str = "pending"
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    rejection_reason: str | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ShiftWishReject(BaseModel):
    rejection_reason: str | None = None


@router.post("", response_model=ShiftWishResponse, status_code=status.HTTP_201_CREATED)
def create_shift_wish(
    data: ShiftWishCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not team_service.user_can_access_employee(db, current_user, data.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    wish = ShiftWish(
        employee_id=data.employee_id,
        date=data.date,
        week=wish_week_for_date(data.date),
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
    status: str | None = Query(None),
):
    query = db.query(ShiftWish)
    if current_user.role == "planer":
        team_ids = team_service.get_team_ids_for_user(db, current_user)
        if team_ids:
            query = team_service.filter_query_by_team_scope(query, ShiftWish, team_ids)
        else:
            query = query.filter(ShiftWish.employee_id == -1)
    elif current_user.role != "admin":
        query = query.filter(ShiftWish.employee_id == current_user.employee_id)
    if status:
        query = query.filter(ShiftWish.status == status)
    total = query.count()
    items = query.order_by(ShiftWish.date).offset(pagination.offset).limit(pagination.limit).all()
    return PaginatedResponse(items=items, total=total, offset=pagination.offset, limit=pagination.limit)


@router.get("/{wish_id}", response_model=ShiftWishResponse)
def get_shift_wish(
    wish_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    response: Response = None,
):
    wish = db.query(ShiftWish).filter(ShiftWish.id == wish_id).first()
    if not wish:
        raise NotFoundException(detail="Shift wish not found")
    if not team_service.user_can_access_employee(db, current_user, wish.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    if response is not None:
        set_etag_header(response, wish, "date", "type", "status")
    return wish


@router.put("/{wish_id}", response_model=ShiftWishResponse)
def update_shift_wish(
    wish_id: int,
    data: ShiftWishUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    if_match: str | None = Header(None, alias="If-Match"),
    response: Response = None,
):
    wish = db.query(ShiftWish).filter(ShiftWish.id == wish_id).first()
    if not wish:
        raise NotFoundException(detail="Shift wish not found")

    try:
        check_etag_conflict(wish, if_match, "date", "type", "status")
    except ConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shift wish was modified by another user. Please refresh and try again.",
        )

    if not team_service.user_can_access_employee(db, current_user, wish.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    if data.employee_id is not None:
        if not team_service.user_can_access_employee(db, current_user, data.employee_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized",
            )
        wish.employee_id = data.employee_id
    if data.date is not None:
        wish.date = data.date
        wish.week = wish_week_for_date(data.date)
    if data.type is not None:
        wish.type = data.type
    if data.note is not None:
        wish.note = data.note
    if data.status is not None:
        if current_user.role == "user":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins or planners can update wish status",
            )
        wish.status = data.status
    db.add(wish)
    db.commit()
    db.refresh(wish)
    if response is not None:
        set_etag_response(response, wish, "date", "type", "status")
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
    if not team_service.user_can_access_employee(db, current_user, wish.employee_id):
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
    user: User = Depends(require_admin_or_planer),
):
    wish = db.query(ShiftWish).filter(ShiftWish.id == wish_id).first()
    if not wish:
        raise NotFoundException(detail="Shift wish not found")
    if not team_service.user_can_access_employee(db, user, wish.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wish belongs to an employee outside of your team scope",
        )
    wish.status = WishStatus.APPROVED.value
    wish.reviewed_by = user.id
    wish.reviewed_at = datetime.now(UTC)
    wish.rejection_reason = None
    db.add(wish)
    db.commit()
    db.refresh(wish)

    # Create notification for the employee's linked user
    from app.db.models.employee import Employee

    employee = db.query(Employee).filter(Employee.id == wish.employee_id).first()
    if employee and employee.user_id:
        create_notification_and_push(
            db=db,
            user_id=employee.user_id,
            notification_type=NotificationType.WISH_APPROVED.value,
            title="Wunsch genehmigt",
            message=f"Dein Schichtwunsch für {wish.date} wurde genehmigt.",
            data={"wish_id": wish.id, "date": str(wish.date), "type": wish.type},
            push_url="/employee-view",
            push_tag="wish_approved",
        )

    return wish


@router.put("/{wish_id}/reject", response_model=ShiftWishResponse)
def reject_shift_wish(
    wish_id: int,
    body: ShiftWishReject,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_planer),
):
    wish = db.query(ShiftWish).filter(ShiftWish.id == wish_id).first()
    if not wish:
        raise NotFoundException(detail="Shift wish not found")
    if not team_service.user_can_access_employee(db, user, wish.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wish belongs to an employee outside of your team scope",
        )
    wish.status = WishStatus.REJECTED.value
    wish.reviewed_by = user.id
    wish.reviewed_at = datetime.now(UTC)
    wish.rejection_reason = body.rejection_reason
    db.add(wish)
    db.commit()
    db.refresh(wish)

    # Create notification for the employee's linked user
    from app.db.models.employee import Employee

    employee = db.query(Employee).filter(Employee.id == wish.employee_id).first()
    if employee and employee.user_id:
        reason_text = f" Grund: {body.rejection_reason}" if body.rejection_reason else ""
        create_notification_and_push(
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
            push_url="/employee-view",
            push_tag="wish_rejected",
        )

    return wish
