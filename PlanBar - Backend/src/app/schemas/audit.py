from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import PaginationResponse


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


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    pagination: PaginationResponse


class SuspiciousPatternResponse(BaseModel):
    pattern_type: str
    description: str
    count: int
    details: list[AuditLogResponse]
