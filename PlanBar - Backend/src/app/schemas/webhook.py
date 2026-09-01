from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


VALID_EVENTS = {
    "schedule.created",
    "schedule.published",
    "shift.assigned",
    "shift.swapped",
    "shift.modified",
    "employee.created",
    "employee.updated",
    "leave.requested",
    "leave.approved",
    "leave.rejected",
    "test.ping",
}


class WebhookCreate(BaseModel):
    url: str
    events: list[str]

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v):
        if not v:
            raise ValueError("At least one event must be specified")
        return v


class WebhookUpdate(BaseModel):
    url: str | None = None
    events: list[str] | None = None
    active: bool | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class WebhookResponse(BaseModel):
    id: int
    url: str
    events: list[str]
    active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class WebhookDetailResponse(WebhookResponse):
    secret: str


class WebhookSecretResponse(BaseModel):
    id: int
    url: str
    secret: str
    events: list[str]
    active: bool

    model_config = {"from_attributes": True}


class WebhookLogResponse(BaseModel):
    id: int
    webhook_id: int
    event: str
    request_url: str
    request_body: str | None
    response_status: int | None
    response_body: str | None
    success: bool
    error_message: str | None
    attempt: int
    dead_letter: bool
    created_at: str

    model_config = {"from_attributes": True}


class TestEventRequest(BaseModel):
    event: str = "test.ping"
    data: dict[str, Any] = {}


class TestEventResponse(BaseModel):
    status: str
