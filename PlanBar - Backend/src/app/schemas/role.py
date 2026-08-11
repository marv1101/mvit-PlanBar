from datetime import datetime

from pydantic import BaseModel, Field


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    permissions: str | None = None


class RoleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    permissions: str | None = None


class RoleResponse(BaseModel):
    id: int
    name: str
    color: str | None = None
    permissions: str | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
