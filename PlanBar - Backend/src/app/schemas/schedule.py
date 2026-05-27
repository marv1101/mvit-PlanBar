from datetime import date, datetime, time
from typing import Any, Optional

from pydantic import BaseModel, Field


class ShiftplanBase(BaseModel):
    employee_id: int
    date: date
    shift_id: str = Field(..., max_length=50)
    start_time: time
    end_time: time
    week: Optional[str] = Field(None, pattern=r"^[AB]$")
    break_start: Optional[str] = None
    break_end: Optional[str] = None
    notes: Optional[str] = None


class ShiftplanCreate(ShiftplanBase):
    pass


class ShiftplanUpdate(BaseModel):
    employee_id: Optional[int] = None
    date: Optional[date] = None
    shift_id: Optional[str] = Field(None, max_length=50)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    week: Optional[str] = Field(None, pattern=r"^[AB]$")
    break_start: Optional[str] = None
    break_end: Optional[str] = None
    notes: Optional[str] = None


class ShiftplanBatchReplace(BaseModel):
    shiftplans: list[ShiftplanCreate]


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
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    role_requirements: Optional[Any] = None
    shiftplans: list[ShiftplanCreate] = []


class ScheduleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    week_type: Optional[str] = Field(None, pattern=r"^[AB]$")


class ScheduleResponse(ScheduleBase):
    id: int
    status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    role_requirements: Optional[Any] = None
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
