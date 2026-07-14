from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AvailabilityEntry(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    available: bool = True
    note: Optional[str] = None


class AvailabilityUpdate(BaseModel):
    entries: list[AvailabilityEntry]


class AvailabilityResponse(BaseModel):
    id: int
    employee_id: int
    day_of_week: int
    available: bool
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
