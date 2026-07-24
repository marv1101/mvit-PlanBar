from datetime import date as Date, datetime, time
from typing import Any

from pydantic import BaseModel, Field

from app.core.enums import ScheduleStatus


class ShiftplanBase(BaseModel):
    employee_id: int
    date: Date
    shift_id: str = Field(..., max_length=50)
    start_time: time
    end_time: time
    week: str | None = Field(None, pattern=r"^[AB]$")
    break_start: str | None = None
    break_end: str | None = None
    label: str | None = Field(None, max_length=100)
    notes: str | None = None


class ShiftplanCreate(ShiftplanBase):
    pass


class ShiftplanUpdate(BaseModel):
    employee_id: int | None = None
    date: Date | None = None
    shift_id: str | None = Field(None, max_length=50)
    start_time: time | None = None
    end_time: time | None = None
    week: str | None = Field(None, pattern=r"^[AB]$")
    break_start: str | None = None
    break_end: str | None = None
    label: str | None = Field(None, max_length=100)
    notes: str | None = None


class ShiftplanBatchReplace(BaseModel):
    shiftplans: list[ShiftplanCreate]


class ShiftplanResponse(ShiftplanBase):
    id: int
    schedule_id: int
    metadata_json: Any | None = None
    metrics_json: Any | None = None
    diagnostics_json: Any | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScheduleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    week_type: str | None = Field(None, pattern=r"^[AB]$")


class ScheduleCreate(ScheduleBase):
    start_date: Date | None = None
    end_date: Date | None = None
    role_requirements: Any | None = None
    shift_templates: Any | None = None
    shiftplans: list[ShiftplanCreate] = []


class ScheduleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    week_type: str | None = Field(None, pattern=r"^[AB]$")
    status: ScheduleStatus | None = None
    shift_templates: Any | None = None


class ScheduleResponse(ScheduleBase):
    id: int
    status: str
    start_date: Date | None = None
    end_date: Date | None = None
    role_requirements: Any | None = None
    shift_templates: Any | None = None
    tito_job_id: int | None = None
    metadata_json: Any | None = None
    metrics_json: Any | None = None
    diagnostics_json: Any | None = None
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
    date_range: tuple[Date, Date] | None = None


# ── ArbZG compliance response schemas ──────────────────────────────────────
class ArbZgViolationResponse(BaseModel):
    rule: str
    message: str
    employee_id: int
    shift_date: Date | None = None
    details: dict[str, Any] | None = None


class ArbZgCheckResponse(BaseModel):
    is_valid: bool
    violations: list[ArbZgViolationResponse] = []


class ScheduleWithArbzgResponse(ScheduleResponse):
    """Schedule response that includes ArbZG compliance warnings."""

    arbZgWarnings: list[ArbZgViolationResponse] = []
