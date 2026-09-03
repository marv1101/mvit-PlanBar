from datetime import datetime, timezone
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError, model_validator

# ============================================================================
# Metadata Model
# ============================================================================


class Metadata(BaseModel):
    """Metadata for a job."""

    jobId: str | None = Field(default=None, description="Unique job identifier")
    tenantId: int = Field(..., ge=1, description="Tenant ID for multi-tenancy")
    priority: int = Field(default=0, ge=0, description="Job priority (higher = more urgent)")
    timestamp: str | None = Field(default=None, description="ISO 8601 timestamp")
    idempotency_key: str | None = Field(default=None, description="For idempotent job processing")
    callback_url: str | None = Field(default=None, description="URL for callback after processing")


# ============================================================================
# Shift Template Model
# ============================================================================


class ShiftTemplate(BaseModel):
    """Template for a shift type."""

    id: str = Field(..., description="Unique shift identifier")
    name: str = Field(..., description="Human-readable shift name")
    startTime: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="Start time in HH:MM format")
    endTime: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="End time in HH:MM format")
    minBreakMinutes: int | None = Field(default=None, ge=0, description="Minimum break in minutes")
    skills: list[str] | None = Field(default=None, description="Required skills for this shift")
    color: str | None = Field(default=None, description="Color code for UI display")


# ============================================================================
# Requirement Model
# ============================================================================


class Requirement(BaseModel):
    """Shift requirement for a specific time slot."""

    # Support both old and new field names
    shiftTemplateId: str | None = Field(default=None, description="Reference to shift template (new)")
    shiftId: str | None = Field(default=None, alias="shiftId", description="Reference to shift template (old)")

    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Date in YYYY-MM-DD format")
    startTime: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$", description="Start time override")
    endTime: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$", description="End time override")
    count: int | None = Field(default=None, ge=1, description="Number of employees needed (min, new)")
    maxCount: int | None = Field(default=None, ge=1, description="Maximum employees allowed (max)")
    neededSkills: dict[str, int] | None = Field(default=None, description="Required skills with counts (old)")
    skills: list[str] | None = Field(default=None, description="Required skills (new)")

    @model_validator(mode="after")
    def normalize_requirement_fields(self) -> "Requirement":
        """Normalize old field names to new ones."""
        # Handle shift ID (bidirectional)
        if self.shiftId and not self.shiftTemplateId:
            self.shiftTemplateId = self.shiftId
        if self.shiftTemplateId and not self.shiftId:
            self.shiftId = self.shiftTemplateId

        # Handle skills - convert neededSkills dict to list
        if self.neededSkills:
            self.skills = list(self.neededSkills.keys())

        # Handle count
        if self.neededSkills and self.count is None:
            self.count = sum(self.neededSkills.values())

        # Default count to 1 when not specified
        if self.count is None:
            self.count = 1

        if self.maxCount is not None and self.count is not None and self.maxCount < self.count:
            raise ValueError(f"maxCount ({self.maxCount}) must be >= count ({self.count})")

        if not self.shiftTemplateId:
            raise ValueError("Requirement must contain either shiftTemplateId or shiftId")

        return self


# ============================================================================
# Employee Model
# ============================================================================


class Employee(BaseModel):
    """Employee data for scheduling."""

    id: str = Field(..., description="Unique employee identifier")
    name: str = Field(..., description="Employee name")
    role: str | None = Field(default=None, description="Primary role of the employee")
    contractHours: float | None = Field(default=None, gt=0, description="Weekly contract hours (new)")
    contract: dict[str, Any] | None = Field(default=None, description="Contract details (old)")
    maxDailyHours: float | None = Field(default=None, gt=0, description="Maximum daily working hours")
    skills: list[str] | None = Field(default=None, description="Employee skills")
    breakMinutes: int | None = Field(default=None, ge=0, description="Preferred break in minutes")
    maxConsecutiveDays: int | None = Field(default=None, ge=1, le=31, description="Maximum consecutive working days")
    minFreeSundaysPerYear: int | None = Field(default=None, ge=0, le=52, description="Minimum free Sundays per year")
    forbiddenDates: list[str] | None = Field(default=None, description="Forbidden dates (old)")
    currentBalanceHours: float | None = Field(default=0.0, description="Aktueller Zeitkontostand in Stunden")
    isNightWorker: bool = Field(default=False, description="Nachtarbeitnehmer i.S.d. ArbZG § 2 Abs. 5")
    isShiftWorker: bool = Field(
        default=False, description="Schichtarbeiter i.S.d. ArbZG § 21 (erlaubt verkürzte Ruhezeit, sofern konfiguriert)"
    )
    isMinor: bool = Field(default=False, description="Minderjährig (JArbSchG-Kernregeln werden erzwungen)")
    protectionUntil: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Mutterschutz-Beschäftigungsverbot bis einschließlich dieses Datums (MuSchG)",
    )
    nightWorkerExamDate: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Datum der letzten arbeitsmedizinischen Eignungsuntersuchung (ArbZG § 6 Abs. 1)",
    )
    protectedDaysWorkedYTD: int = Field(
        default=0,
        ge=0,
        description="Anzahl bereits gearbeiteter Sonntage/Gesetzlicher Feiertage im laufenden Kalenderjahr (§ 11 Abs. 1 ArbZG)",
    )

    @model_validator(mode="after")
    def normalize_employee_fields(self) -> "Employee":
        """Normalize old field names to new ones."""
        # Handle contract - extract weeklyHours if contract dict exists
        if self.contract and self.contractHours is None:
            self.contractHours = self.contract.get("weeklyHours", 40.0)

        # Handle contract - extract currentBalanceHours for backward compatibility
        if self.contract and self.currentBalanceHours == 0.0:
            self.currentBalanceHours = self.contract.get("currentBalanceHours", 0.0)

        # Reverse: build contract dict from contractHours for solver compatibility
        if self.contractHours is not None and self.contract is None:
            self.contract = {"weeklyHours": self.contractHours}

        return self


# ============================================================================
# Wish Models
# ============================================================================


class Wish(BaseModel):
    """Employee shift wish."""

    employeeId: str = Field(..., description="Employee ID")
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Date in YYYY-MM-DD format")
    shiftTemplateId: str | None = Field(default=None, description="Preferred shift template (new)")
    shiftId: str | None = Field(default=None, alias="shiftId", description="Preferred shift template (old)")
    type: str = Field(default="OFF", description="Wish type: OFF, SHIFT, etc.")
    priority: int = Field(default=0, ge=0, le=10, description="Wish priority (new)")
    weight: int | None = Field(default=None, description="Wish weight (old)")
    comment: str | None = Field(default=None, description="Comment (old)")

    @model_validator(mode="after")
    def normalize_wish_fields(self) -> "Wish":
        """Normalize old field names to new ones."""
        # Handle shift ID
        if self.shiftId and not self.shiftTemplateId:
            self.shiftTemplateId = self.shiftId
        if self.shiftTemplateId and not self.shiftId:
            self.shiftId = self.shiftTemplateId

        # Handle priority/weight (bidirectional, damit weight nie None bleibt,
        # wenn eine der beiden Angaben existiert)
        if self.weight is not None and self.priority == 0:
            self.priority = self.weight
        if self.weight is None and self.priority > 0:
            self.weight = self.priority

        return self


# ============================================================================
# Config Model
# ============================================================================


class Config(BaseModel):
    """Configuration for the scheduling run.

    Alle Regel-Parameter akzeptieren camelCase UND snake_case (AliasChoices),
    damit Aufrufer wie das PlanBar-Backend beide Konventionen nutzen koennen,
    ohne dass Parameter still verworfen werden (extra="ignore").
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    schemaVersion: str = Field(default="1.0", description="Schema version for backward compatibility")
    startDate: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        validation_alias=AliasChoices("startDate", "start_date"),
        description="Planning period start",
    )
    endDate: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        validation_alias=AliasChoices("endDate", "end_date"),
        description="Planning period end",
    )
    maxConsecutiveDays: int | None = Field(
        default=6,
        ge=1,
        le=31,
        validation_alias=AliasChoices("maxConsecutiveDays", "max_consecutive_days"),
        description="Max consecutive working days",
    )
    minRestTimeHours: float | None = Field(
        default=11,
        gt=0,
        validation_alias=AliasChoices("minRestTimeHours", "min_rest_time_hours"),
        description="Minimum rest time between shifts in hours (ArbZG § 5)",
    )
    maxDailyWorkHours: float | None = Field(
        default=10,
        gt=0,
        validation_alias=AliasChoices("maxDailyWorkHours", "max_daily_work_hours"),
        description="Maximum daily working hours (ArbZG § 3, Netto)",
    )
    minFreeSundaysPerYear: int | None = Field(
        default=15,
        ge=0,
        le=52,
        validation_alias=AliasChoices("minFreeSundaysPerYear", "min_free_sundays_per_year"),
        description="Minimum free Sundays per year (ArbZG § 11 Abs. 1)",
    )
    holidayDates: list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices("holidayDates", "holiday_dates"),
        description="List of public holiday dates (YYYY-MM-DD) treated like Sundays per ArbZG §9",
    )
    defaultWeeklyHours: float | None = Field(
        default=40.0,
        gt=0,
        validation_alias=AliasChoices("defaultWeeklyHours", "default_weekly_hours"),
        description="Default weekly contract hours",
    )
    maxSameShiftConsecutive: int | None = Field(
        default=0,
        ge=0,
        le=14,
        validation_alias=AliasChoices("maxSameShiftConsecutive", "max_same_shift_consecutive"),
        description="Max consecutive days with same shift type (0 = disabled)",
    )
    solverTimeoutSeconds: int | None = Field(
        default=300,
        gt=0,
        validation_alias=AliasChoices("solverTimeoutSeconds", "solver_timeout_seconds"),
        description="Solver timeout in seconds (vom Worker als Timeout-Budget genutzt)",
    )
    maximizeStaffing: bool = Field(
        default=False,
        validation_alias=AliasChoices("maximizeStaffing", "maximize_staffing"),
        description="Maximize employee utilization by filling optional slots",
    )
    restTimeShiftWorkersHours: float | None = Field(
        default=None,
        ge=9,
        le=11,
        validation_alias=AliasChoices("restTimeShiftWorkersHours", "rest_time_shift_workers_hours"),
        description="Verkürzte Ruhezeit für Schichtarbeiter (ArbZG § 21 Abs. 1: um bis zu 2h auf mind. 9h verkürzbar); None = pauschale minRestTimeHours",
    )
    nightWindowStart: str = Field(
        default="23:00",
        pattern=r"^\d{2}:\d{2}$",
        validation_alias=AliasChoices("nightWindowStart", "night_window_start"),
        description="Beginn des Nachtzeitfensters (ArbZG § 2 Abs. 3, default 23:00)",
    )
    nightWindowEnd: str = Field(
        default="06:00",
        pattern=r"^\d{2}:\d{2}$",
        validation_alias=AliasChoices("nightWindowEnd", "night_window_end"),
        description="Ende des Nachtzeitfensters (ArbZG § 2 Abs. 3, default 06:00)",
    )
    nightWorkMaxHours: float = Field(
        default=10.0,
        gt=0,
        validation_alias=AliasChoices("nightWorkMaxHours", "night_work_max_hours"),
        description="Maximale Arbeitszeit von Nachtarbeitnehmern an Nachtschichten (ArbZG § 6 Abs. 2)",
    )
    maxWeeklyHoursLaw: float = Field(
        default=48.0,
        gt=0,
        validation_alias=AliasChoices("maxWeeklyHoursLaw", "max_weekly_hours_law"),
        description="Gesetzliche Wochenobergrenze (ArbZG § 3: 48h im Durchschnitt von 6 Monaten/24 Wochen)",
    )
    numSearchWorkers: int = Field(
        default=8,
        ge=1,
        validation_alias=AliasChoices("numSearchWorkers", "num_search_workers"),
        description="CP-SAT parallel workers (1 = voll deterministisch)",
    )
    randomSeed: int = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices("randomSeed", "random_seed"),
        description="CP-SAT random seed für reproduzierbare Läufe",
    )


class PreShift(BaseModel):
    """Vorangehende, bereits fixierte Schicht eines Mitarbeiters.

    Wird vom Aufrufer übergeben, damit der Solver Ruhezeit (§ 5 ArbZG),
    Folgetage-Ketten, Wochenstunden und Sonntagskontingente über die
    Planungsgrenze hinaus prüfen kann.
    """

    employeeId: str = Field(..., description="Employee ID (muss in employees referenziert sein)")
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Date in YYYY-MM-DD format")
    startTime: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="Start time in HH:MM format")
    endTime: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="End time in HH:MM format")


# ============================================================================
# Main Job Payload Model
# ============================================================================


class JobPayload(BaseModel):
    """Main job payload with full validation."""

    model_config = ConfigDict(extra="ignore")  # Ignore unknown fields (e.g. tenant_id from backend)

    metadata: Metadata
    config: Config
    shiftTemplates: list[ShiftTemplate]
    requirements: list[Requirement]
    employees: list[Employee]
    wishes: list[Wish] | None = Field(default=None)
    preShifts: list[PreShift] | None = Field(default=None)

    @model_validator(mode="after")
    def validate_references(self) -> "JobPayload":
        """Validate that all references exist."""
        shift_ids = {st.id for st in self.shiftTemplates}
        employee_ids = {e.id for e in self.employees}

        # Duplicate shift template ids would silently overwrite each other in the solver
        if len(shift_ids) != len(self.shiftTemplates):
            seen: set[str] = set()
            duplicates: set[str] = set()
            for st in self.shiftTemplates:
                if st.id in seen:
                    duplicates.add(st.id)
                seen.add(st.id)
            raise ValueError(f"Duplicate shift template ids: {sorted(duplicates)}")

        # Validate shift references in requirements
        for req in self.requirements:
            if req.shiftTemplateId not in shift_ids:
                raise ValueError(f"Requirement references unknown shift template: {req.shiftTemplateId}")

        # Validate shift references in wishes
        if self.wishes:
            for wish in self.wishes:
                if wish.shiftTemplateId is not None and wish.shiftTemplateId not in shift_ids:
                    raise ValueError(f"Wish references unknown shift template: {wish.shiftTemplateId}")

        # Validate employee references in wishes
        if self.wishes:
            for wish in self.wishes:
                if wish.employeeId not in employee_ids:
                    raise ValueError(f"Wish references unknown employee: {wish.employeeId}")

        # Validate employee references in preShifts
        if self.preShifts:
            for pre in self.preShifts:
                if pre.employeeId not in employee_ids:
                    raise ValueError(f"PreShift references unknown employee: {pre.employeeId}")

        return self

    @model_validator(mode="after")
    def validate_date_range(self) -> "JobPayload":
        """Validate that startDate is before endDate and all requirement dates lie within the planning period."""

        start = datetime.strptime(self.config.startDate, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(self.config.endDate, "%Y-%m-%d").replace(tzinfo=timezone.utc)

        if start >= end:
            raise ValueError("startDate must be before endDate")

        # Requirements außerhalb des Planungszeitraums verfälschen Wochen-Fairness,
        # Sonntagsquoten und Kalenderketten-Fenster und werden abgewiesen (C7)
        for req in self.requirements:
            req_date = datetime.strptime(req.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if req_date < start or req_date > end:
                raise ValueError(
                    f"Requirement date {req.date} is outside the planning period "
                    f"[{self.config.startDate}, {self.config.endDate}]"
                )

        return self


# ============================================================================
# Validation Function (Backward Compatibility)
# ============================================================================


def validate_job_payload(payload: dict) -> JobPayload:
    """
    Validiert das JSON-Payload gegen Pydantic-Schema.
    Gibt das validierte JobPayload-Objekt zurück.

    Args:
        payload: Das zu validierende JSON-Objekt

    Returns:
        JobPayload: Validiertes Pydantic-Modell

    Raises:
        ValueError: Wenn Validierung fehlschlägt
    """
    try:
        return JobPayload.model_validate(payload)
    except (ValueError, TypeError, KeyError):
        raise
    except ValidationError as e:
        raise ValueError(f"Validation failed: {e}")


def extract_tenant_id(metadata: dict | None) -> str | None:
    """Extrahiert die Tenant-ID aus einem Metadata-Dict.

    Akzeptiert sowohl den schema-konformen camelCase-Key ``tenantId`` als
    auch den snake_case-Key ``tenant_id`` (wie er vom PlanBar-Backend
    gesendet wird). Der Wert wird normalisiert auf ``str`` zurückgegeben,
    damit Vergleiche gegen die ``TEXT``-Spalte ``tenant_id`` in der DB
    typstabil bleiben (B2/B10).

    Returns:
        Tenant-ID als ``str`` oder ``None``, wenn keine vorhanden.
    """
    if not metadata:
        return None
    raw = metadata.get("tenantId")
    if raw is None:
        raw = metadata.get("tenant_id")
    if raw is None:
        return None
    return str(raw)


# ============================================================================
# Result Models (for output)
# ============================================================================


class Assignment(BaseModel):
    """Assignment of employee to shift."""

    employeeId: str
    date: str
    shiftTemplateId: str
    startTime: str
    endTime: str
    name: str = ""


class SolverStatus:
    """Solver status constants."""

    SUCCESS = "SUCCESS"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    TIMEOUT = "TIMEOUT"


class SolveResult(BaseModel):
    """Result of the optimization run."""

    status: str = Field(..., description="Solver status (SUCCESS, FEASIBLE, INFEASIBLE, TIMEOUT)")
    assignments: list[Assignment] = Field(default_factory=list, description="Schedule assignments")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Optimization metrics")
    constraintViolations: list[dict[str, Any]] | None = Field(
        default=None, description="Details about constraint violations (if any)"
    )
    solverInfo: dict[str, Any] | None = Field(
        default=None,
        description="Solver-specific information (runtime, iterations, etc.)",
    )


class JobResult(BaseModel):
    """Complete job result with metadata."""

    jobId: str
    tenantId: int
    status: str
    result: SolveResult
    createdAt: str
