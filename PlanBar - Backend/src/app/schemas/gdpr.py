from datetime import datetime

from pydantic import BaseModel


class DataAccessResponse(BaseModel):
    personal_data: dict
    processing_purposes: list[str]
    data_recipients: list[str]
    retention_periods: dict
    rights: list[str]


class ProcessingRestrictionResponse(BaseModel):
    message: str
    restricted: bool


class ObjectionResponse(BaseModel):
    message: str
    objection_filed: bool
    objection_date: datetime | None = None


class AutomatedDecisionInfo(BaseModel):
    automated_decisions_used: bool
    details: dict
    right_to_review: str
