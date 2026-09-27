from datetime import date as Date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Callback statuses per contract v2 (plus legacy "COMPLETED" tolerated)
_CALLBACK_STATUSES = {"SUCCESS", "FEASIBLE", "INFEASIBLE", "TIMEOUT", "FAILED", "COMPLETED"}


class TiTOAssignment(BaseModel):
    """Assignment element per callback contract v2.

    employeeId is an int in contract v2; the legacy "emp_123" string form
    is still accepted during the transition (parsed robustly by the
    callback processing, invalid values drop the assignment with an
    INVALID_ASSIGNMENT violation instead of failing the request).
    """

    employeeId: int | str
    date: Date
    shiftId: str
    startTime: str
    endTime: str
    breakMinutes: int = 0
    name: str = ""


class TiTOMetadata(BaseModel):
    status: str = ""
    solveTimeSeconds: float = 0.0
    timestamp: str = ""


class TiTORequestMetadata(BaseModel):
    """Metadata sent with job submission to TiTO"""

    callback_url: str
    idempotency_key: str | None = None
    tenant_id: str | None = None


class TiTOMetrics(BaseModel):
    wishFulfillmentRate: float = 0.0
    totalObjectiveScore: float = 0.0
    employeeUtilization: dict[str, float] = {}
    violations: list[dict[str, Any]] | None = None
    # Der Solver liefert employeeFairness als dict[str, dict] (pro Mitarbeiter
    # targetHours/scheduledHours/...). float bleibt als Legacy-Fallback akzeptiert.
    employeeFairness: float | dict[str, dict[str, float]] | None = None


class TiTODiagnostics(BaseModel):
    isOptimal: bool = False
    info: str = ""
    infeasibilityReasons: list[str] = []


class TiTOSolution(BaseModel):
    """Legacy (pre-v2) nested solution shape; still accepted on callbacks."""

    assignments: list[TiTOAssignment] = []
    unassignedRequirements: list[dict[str, Any]] = []


class TiTOJobResponse(BaseModel):
    """Response of POST /jobs — TiTO replies with camelCase jobId.

    Both ``jobId`` (alias) and ``job_id`` are accepted; optional fields
    tolerate partial TiTO responses.
    """

    model_config = ConfigDict(populate_by_name=True)

    job_id: int = Field(..., alias="jobId")
    status: str
    metadata: TiTOMetadata | None = None
    solution: TiTOSolution | None = None
    metrics: TiTOMetrics | None = None
    diagnostics: TiTODiagnostics | None = None


class TiTOJobStatus(BaseModel):
    """Status of a TiTO job — created_at/updated_at are optional (TiTO may omit them)."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: int = Field(..., alias="jobId")
    status: str
    created_at: str | None = None
    updated_at: str | None = None


class TiTOJobRequest(BaseModel):
    """Job submission payload matching the real TiTO JobPayload format."""

    metadata: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    shiftTemplates: list[dict[str, Any]] = []
    requirements: list[dict[str, Any]] = []
    employees: list[dict[str, Any]] = []
    wishes: list[dict[str, Any]] = []
    preShifts: list[dict[str, Any]] = []


class TiTOCallbackPayload(BaseModel):
    """TiTO callback payload per contract v2 (flat result or error shape).

    Result:  job_id, status SUCCESS|FEASIBLE|INFEASIBLE|TIMEOUT, assignments,
             unassignedRequirements, violations, metrics, diagnostics
    Error:   job_id, status FAILED, error, attempts

    The legacy nested shape (metadata/solution) is accepted during the
    transition from the old TiTO callback format.
    """

    model_config = ConfigDict(populate_by_name=True)

    job_id: int = Field(..., alias="jobId")
    status: str
    assignments: list[TiTOAssignment] = []
    unassignedRequirements: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    metrics: TiTOMetrics | None = None
    diagnostics: TiTODiagnostics | None = None
    error: str | None = None
    attempts: int | None = None
    # Legacy (pre-v2) nested shape — optional transition support
    metadata: TiTOMetadata | None = None
    solution: TiTOSolution | None = None

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        normalized = (value or "").strip().upper()
        if normalized not in _CALLBACK_STATUSES:
            raise ValueError(
                f"Unsupported callback status '{value}' (expected one of {sorted(_CALLBACK_STATUSES - {'COMPLETED'})})"
            )
        return normalized
