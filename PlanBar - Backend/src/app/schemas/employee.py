from datetime import datetime

from pydantic import BaseModel, Field


class EmployeeBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=64)
    last_name: str = Field(..., min_length=1, max_length=64)
    email: str | None = None
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    working_hours_json: str | None = None
    break_start: str | None = None
    break_end: str | None = None
    max_work_hours: float | None = None
    role_ids: list[int] = []


class EmployeeCreate(EmployeeBase):
    user_id: int | None = None
    team_ids: list[int] = []


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=64)
    last_name: str | None = Field(None, min_length=1, max_length=64)
    email: str | None = None
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    working_hours_json: str | None = None
    break_start: str | None = None
    break_end: str | None = None
    max_work_hours: float | None = None
    user_id: int | None = None
    role_ids: list[int] | None = None
    team_ids: list[int] | None = None


class EmployeeResponse(EmployeeBase):
    id: int
    user_id: int | None = None
    team_ids: list[int] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContractBase(BaseModel):
    weekly_working_hours: float = Field(..., gt=0, le=168)
    break_time: int = Field(30, ge=0)
    hired_role: str | None = None


class ContractCreate(ContractBase):
    employee_id: int


class ContractUpdate(BaseModel):
    weekly_working_hours: float | None = Field(None, gt=0, le=168)
    break_time: int | None = Field(None, ge=0)
    hired_role: str | None = None


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
    manual_adjustment_hours: float = 0.0
    adjustment_reason: str | None = None


class TimecardCreate(TimecardBase):
    employee_id: int


class TimecardUpdate(BaseModel):
    week: int | None = Field(None, ge=1, le=53)
    year: int | None = Field(None, ge=2020, le=2100)
    balance: float | None = None
    scheduled_hours: float | None = None
    actual_hours: float | None = None
    contract_hours: float | None = None
    manual_adjustment_hours: float | None = None
    adjustment_reason: str | None = None


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
    manual_adjustment: float = 0.0
    adjustment_reason: str | None = None
    total_change: float = 0.0


class TimeAccountProjected(BaseModel):
    from_schedule: float
    expected_balance_after: float


class TimeAccountResponse(BaseModel):
    employee_id: int
    employee_name: str
    current_balance: float
    history: list[TimeAccountEntry]
    projected: TimeAccountProjected | None = None


class TimeAccountAdjust(BaseModel):
    delta_hours: float
    reason: str | None = None
