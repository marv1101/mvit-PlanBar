from datetime import datetime

from pydantic import BaseModel, Field


class ShiftSwapCreate(BaseModel):
    requester_shift_id: int
    target_employee_id: int
    target_shift_id: int
    note: str | None = None


class ShiftSwapUpdate(BaseModel):
    status: str | None = Field(None, pattern=r"^(pending|approved|rejected)$")
    rejection_reason: str | None = None


class ShiftSwapResponse(BaseModel):
    id: int
    employee_id: int
    requester_shift_id: int
    target_employee_id: int
    target_shift_id: int
    status: str = "pending"
    note: str | None = None
    approved_by: int | None = None
    reviewed_at: datetime | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShiftSwapReject(BaseModel):
    rejection_reason: str | None = None
