from datetime import datetime
from typing import Any, Generic, TypeVar

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


class AuditLogFilter(BaseModel):
    """Filter schema for audit log queries.
    
    Replaces the previous 10-parameter endpoint signature with a single
    filter object. Use with FastAPI Depends() for query parameter binding.
    """
    user_id: int | None = None
    action: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict, excluding None values for flexible SQLAlchemy filtering."""
        return {k: v for k, v in self.model_dump().items() if v is not None}
