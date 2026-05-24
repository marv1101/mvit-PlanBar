from datetime import date, datetime, time
from typing import Any, Optional

from pydantic import BaseModel, Field


class ShiftplanBase(BaseModel):
    employee_id: int
    date: date
    shift_id: str = Field(..., max_length=20)
    start_time: time
    end_time: time
    notes: Optional[str] = None


class ShiftplanCreate(ShiftplanBase):
    pass


class ShiftplanUpdate(BaseModel):
    employee_id: Optional[int] = None
    date: Optional[date] = None
    shift_id: Optional[str] = Field(None, max_length=20)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    notes: Optional[str] = None


class ShiftplanResponse(ShiftplanBase):
    id: int
    schedule_id: int
    metadata_json: Optional[Any] = None
    metrics_json: Optional[Any] = None
    diagnostics_json: Optional[Any] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScheduleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    week_type: Optional[str] = Field(None, pattern=r"^[AB]$")


class ScheduleCreate(ScheduleBase):
    shiftplans: list[ShiftplanCreate] = []


class ScheduleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    week_type: Optional[str] = Field(None, pattern=r"^[AB]$")


class ScheduleResponse(ScheduleBase):
    id: int
    status: str
    tito_job_id: Optional[int] = None
    metadata_json: Optional[Any] = None
    metrics_json: Optional[Any] = None
    diagnostics_json: Optional[Any] = None
    shiftplans: list[ShiftplanResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScheduleSummary(BaseModel):
    id: int
    name: str
    status: str
    total_shifts: int
    total_employees: int
    date_range: Optional[tuple[date, date]] = None
