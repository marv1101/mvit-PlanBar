"""Pydantic schemas for time tracking (Issue #29)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TimeEntryCreate(BaseModel):
    notes: Optional[str] = Field(None, max_length=1000)


class TimeEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    clock_in: datetime
    clock_out: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
