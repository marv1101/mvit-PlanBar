from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None
    action: str
    resource_type: str
    resource_id: str | None
    details: str | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedAuditLogResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int


class AuditLogListResponse(PaginatedAuditLogResponse[AuditLogResponse]):
    pass


class SuspiciousPatternResponse(BaseModel):
    pattern_type: str
    description: str
    count: int
    details: list[AuditLogResponse]
