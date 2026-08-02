from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import NotificationType, ShiftSwapStatus
from app.core.exceptions import NotFoundException
from app.db.models.employee import Employee
from app.db.models.schedule import Shiftplan
from app.db.models.shift_swap import ShiftSwapRequest
from app.db.models.user import User
from app.dependencies import get_current_user, get_db, require_admin_or_planer
from app.schemas.shift_swap import (
    ShiftSwapCreate,
    ShiftSwapReject,
    ShiftSwapResponse,
)
from app.services import team_service
from app.services.notification_service import create_notification


def _swap_in_user_scope(db: Session, swap: ShiftSwapRequest, user) -> bool:
    """Check whether both employees of the swap are within the user's team scope."""
    return team_service.user_can_access_employee(db, user, swap.employee_id) and team_service.user_can_access_employee(
        db, user, swap.target_employee_id
    )


router = APIRouter()


@router.post("", response_model=ShiftSwapResponse, status_code=status.HTTP_201_CREATED)
def create_shift_swap(
    data: ShiftSwapCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user has no linked employee",
        )

    requester_shift = db.query(Shiftplan).filter(Shiftplan.id == data.requester_shift_id).first()
    if not requester_shift:
        raise NotFoundException(detail="Requester shift not found")
    if requester_shift.employee_id != current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requester shift does not belong to you",
        )

    target_shift = db.query(Shiftplan).filter(Shiftplan.id == data.target_shift_id).first()
    if not target_shift:
        raise NotFoundException(detail="Target shift not found")
    if target_shift.employee_id != data.target_employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target shift does not belong to target employee",
        )

    swap = ShiftSwapRequest(
        employee_id=current_user.employee_id,
        requester_shift_id=data.requester_shift_id,
        target_employee_id=data.target_employee_id,
        target_shift_id=data.target_shift_id,
        status=ShiftSwapStatus.PENDING.value,
        note=data.note,
    )
    db.add(swap)
    db.commit()
    db.refresh(swap)

    target_employee = db.query(Employee).filter(Employee.id == data.target_employee_id).first()
    if target_employee and target_employee.user_id:
        create_notification(
            db=db,
            user_id=target_employee.user_id,
            notification_type=NotificationType.SWAP_REQUESTED.value,
            title="Schichttausch angefragt",
            message=f"{current_user.employee.first_name} {current_user.employee.last_name} möchte mit dir die Schicht am {target_shift.date} tauschen.",
            data={"swap_id": swap.id},
        )

    return swap


@router.get("/me", response_model=list[ShiftSwapResponse])
def get_my_shift_swaps(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.employee_id:
        return []
    swaps = (
        db.query(ShiftSwapRequest)
        .filter(
            (ShiftSwapRequest.employee_id == current_user.employee_id)
            | (ShiftSwapRequest.target_employee_id == current_user.employee_id)
        )
        .order_by(ShiftSwapRequest.created_at.desc())
        .all()
    )
    return swaps


@router.put("/{swap_id}/approve", response_model=ShiftSwapResponse)
def approve_shift_swap(
    swap_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_planer),
):
    swap = db.query(ShiftSwapRequest).filter(ShiftSwapRequest.id == swap_id).first()
    if not swap:
        raise NotFoundException(detail="Shift swap not found")
    if not _swap_in_user_scope(db, swap, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Shift swap is outside of your team scope",
        )
    if swap.status != ShiftSwapStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shift swap is not pending",
        )

    requester_shift = db.query(Shiftplan).filter(Shiftplan.id == swap.requester_shift_id).first()
    target_shift = db.query(Shiftplan).filter(Shiftplan.id == swap.target_shift_id).first()
    if not requester_shift or not target_shift:
        raise NotFoundException(detail="One of the shifts no longer exists")

    requester_shift.employee_id = swap.target_employee_id
    target_shift.employee_id = swap.employee_id

    swap.status = ShiftSwapStatus.APPROVED.value
    swap.approved_by = user.id
    swap.reviewed_at = datetime.now(timezone.utc)
    db.add(swap)
    db.commit()
    db.refresh(swap)

    requester_emp = db.query(Employee).filter(Employee.id == swap.employee_id).first()
    target_emp = db.query(Employee).filter(Employee.id == swap.target_employee_id).first()
    if requester_emp and requester_emp.user_id:
        create_notification(
            db=db,
            user_id=requester_emp.user_id,
            notification_type=NotificationType.SWAP_APPROVED.value,
            title="Schichttausch genehmigt",
            message="Dein Schichttausch wurde genehmigt.",
            data={"swap_id": swap.id},
        )
    if target_emp and target_emp.user_id:
        create_notification(
            db=db,
            user_id=target_emp.user_id,
            notification_type=NotificationType.SWAP_APPROVED.value,
            title="Schichttausch genehmigt",
            message="Der Schichttausch wurde genehmigt.",
            data={"swap_id": swap.id},
        )

    return swap


@router.put("/{swap_id}/reject", response_model=ShiftSwapResponse)
def reject_shift_swap(
    swap_id: int,
    body: ShiftSwapReject,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_planer),
):
    swap = db.query(ShiftSwapRequest).filter(ShiftSwapRequest.id == swap_id).first()
    if not swap:
        raise NotFoundException(detail="Shift swap not found")
    if not _swap_in_user_scope(db, swap, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Shift swap is outside of your team scope",
        )
    if swap.status != ShiftSwapStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shift swap is not pending",
        )

    swap.status = ShiftSwapStatus.REJECTED.value
    swap.approved_by = user.id
    swap.reviewed_at = datetime.now(timezone.utc)
    swap.rejection_reason = body.rejection_reason
    db.add(swap)
    db.commit()
    db.refresh(swap)

    requester_emp = db.query(Employee).filter(Employee.id == swap.employee_id).first()
    target_emp = db.query(Employee).filter(Employee.id == swap.target_employee_id).first()
    reason_text = f" Grund: {body.rejection_reason}" if body.rejection_reason else ""
    if requester_emp and requester_emp.user_id:
        create_notification(
            db=db,
            user_id=requester_emp.user_id,
            notification_type=NotificationType.SWAP_REJECTED.value,
            title="Schichttausch abgelehnt",
            message=f"Dein Schichttausch wurde abgelehnt.{reason_text}",
            data={"swap_id": swap.id, "rejection_reason": body.rejection_reason},
        )
    if target_emp and target_emp.user_id:
        create_notification(
            db=db,
            user_id=target_emp.user_id,
            notification_type=NotificationType.SWAP_REJECTED.value,
            title="Schichttausch abgelehnt",
            message=f"Der Schichttausch wurde abgelehnt.{reason_text}",
            data={"swap_id": swap.id, "rejection_reason": body.rejection_reason},
        )

    return swap
