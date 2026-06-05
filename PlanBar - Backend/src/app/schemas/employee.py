from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EmployeeBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=64)
    last_name: str = Field(..., min_length=1, max_length=64)
    email: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    working_hours_json: Optional[str] = None
    break_start: Optional[str] = None
    break_end: Optional[str] = None
    max_work_hours: Optional[float] = None
    role_ids: list[int] = []


class EmployeeCreate(EmployeeBase):
    user_id: Optional[int] = None


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=64)
    last_name: Optional[str] = Field(None, min_length=1, max_length=64)
    email: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    working_hours_json: Optional[str] = None
    break_start: Optional[str] = None
    break_end: Optional[str] = None
    max_work_hours: Optional[float] = None
    user_id: Optional[int] = None
    role_ids: Optional[list[int]] = None


class EmployeeResponse(EmployeeBase):
    id: int
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContractBase(BaseModel):
    weekly_working_hours: float = Field(..., gt=0, le=168)
    break_time: int = Field(30, ge=0)
    hired_role: Optional[str] = None


class ContractCreate(ContractBase):
    employee_id: int


class ContractUpdate(BaseModel):
    weekly_working_hours: Optional[float] = Field(None, gt=0, le=168)
    break_time: Optional[int] = Field(None, ge=0)
    hired_role: Optional[str] = None


class ContractResponse(ContractBase):
    id: int
    employee_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TimecardBase(BaseModel):
    week: int = Field(..., ge=1, le=53)
    year: int = Field(..., ge=2020, le=2100)
    balance: float = 0.0
    scheduled_hours: float = 0.0
    actual_hours: float = 0.0
    contract_hours: float = 0.0


class TimecardCreate(TimecardBase):
    employee_id: int


class TimecardUpdate(BaseModel):
    week: Optional[int] = Field(None, ge=1, le=53)
    year: Optional[int] = Field(None, ge=2020, le=2100)
    balance: Optional[float] = None
    scheduled_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    contract_hours: Optional[float] = None


class TimecardResponse(TimecardBase):
    id: int
    employee_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TimeAccountEntry(BaseModel):
    week: int
    year: int
    scheduled_hours: float
    contract_hours: float
    delta: float
    balance: float


class TimeAccountProjected(BaseModel):
    from_schedule: float
    expected_balance_after: float


class TimeAccountResponse(BaseModel):
    employee_id: int
    current_balance: float
    history: list[TimeAccountEntry]
    projected: TimeAccountProjected | None = None
