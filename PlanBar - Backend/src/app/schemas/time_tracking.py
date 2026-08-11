"""Pydantic schemas for time tracking (Issue #29)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TimeEntryCreate(BaseModel):
    notes: str | None = Field(None, max_length=1000)


class TimeEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    clock_in: datetime
    clock_out: datetime | None = None
    duration_minutes: int | None = None
    notes: str | None = None
    created_at: datetime
