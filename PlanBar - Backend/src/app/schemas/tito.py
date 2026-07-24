from datetime import date
from typing import Any

from pydantic import BaseModel


class TiTOAssignment(BaseModel):
    employeeId: str
    date: date
    shiftId: str
    startTime: str
    endTime: str
    name: str = ""


class TiTOMetadata(BaseModel):
    status: str
    solveTimeSeconds: float
    timestamp: str


class TiTORequestMetadata(BaseModel):
    """Metadata sent with job submission to TiTO"""

    callback_url: str
    idempotency_key: str | None = None
    tenant_id: str | None = None


class TiTOMetrics(BaseModel):
    wishFulfillmentRate: float
    totalObjectiveScore: float
    employeeUtilization: dict[str, float]
    violations: list[dict[str, Any]] | None = None


class TiTODiagnostics(BaseModel):
    isOptimal: bool
    info: str


class TiTOSolution(BaseModel):
    assignments: list[TiTOAssignment]
    unassignedRequirements: list[dict[str, Any]]


class TiTOJobResponse(BaseModel):
    job_id: int
    status: str
    metadata: TiTOMetadata
    solution: TiTOSolution
    metrics: TiTOMetrics
    diagnostics: TiTODiagnostics


class TiTOJobStatus(BaseModel):
    job_id: int
    status: str
    created_at: str
    updated_at: str


class TiTOJobRequest(BaseModel):
    employees: list[dict[str, Any]]
    shiftWishes: list[dict[str, Any]]
    requirements: list[dict[str, Any]]
    constraints: dict[str, Any] | None = None
    metadata: TiTORequestMetadata | None = None


class TiTOCallbackPayload(BaseModel):
    job_id: int
    status: str
    metadata: TiTOMetadata
    solution: TiTOSolution
    metrics: TiTOMetrics
    diagnostics: TiTODiagnostics
