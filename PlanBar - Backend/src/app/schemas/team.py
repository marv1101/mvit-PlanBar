from datetime import datetime

from pydantic import BaseModel, Field


class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    description: str | None = None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    description: str | None = None


class TeamResponse(TeamBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeamWithEmployeesResponse(TeamResponse):
    employee_ids: list[int] = []


class EmployeeTeamAssignment(BaseModel):
    employee_ids: list[int] = []
