from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ShiftSwapCreate(BaseModel):
    requester_shift_id: int
    target_employee_id: int
    target_shift_id: int
    note: Optional[str] = None


class ShiftSwapUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern=r"^(pending|approved|rejected)$")
    rejection_reason: Optional[str] = None


class ShiftSwapResponse(BaseModel):
    id: int
    employee_id: int
    requester_shift_id: int
    target_employee_id: int
    target_shift_id: int
    status: str = "pending"
    note: Optional[str] = None
    approved_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShiftSwapReject(BaseModel):
    rejection_reason: Optional[str] = None
