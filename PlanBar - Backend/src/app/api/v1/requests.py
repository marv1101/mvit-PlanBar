from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.dependencies import get_current_user, get_db
from app.db.models.shift_wish import ShiftWish
from app.db.models.user import User

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


class ShiftWishResponse(BaseModel):
    id: int
    employee_id: int
    date: date
    week: Optional[int] = None
    type: str
    note: Optional[str] = None

    model_config = {"from_attributes": True}


@router.post("", response_model=ShiftWishResponse, status_code=status.HTTP_201_CREATED)
def create_shift_wish(
    data: ShiftWishCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wish = ShiftWish(
        employee_id=data.employee_id,
        date=data.date,
        week=data.week,
        type=data.type,
        note=data.note,
    )
    db.add(wish)
    db.commit()
    db.refresh(wish)
    return wish


@router.get("", response_model=list[ShiftWishResponse])
def list_shift_wishes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(ShiftWish).order_by(ShiftWish.date).all()


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
):
    wish = db.query(ShiftWish).filter(ShiftWish.id == wish_id).first()
    if not wish:
        raise NotFoundException(detail="Shift wish not found")
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
    db.delete(wish)
    db.commit()
