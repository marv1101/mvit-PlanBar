from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, field_serializer
import re


# ============================================================================
# Metadata Model
# ============================================================================

class Metadata(BaseModel):
    """Metadata for a job."""
    jobId: Optional[str] = Field(default=None, description="Unique job identifier")
    tenantId: int = Field(..., ge=1, description="Tenant ID for multi-tenancy")
    priority: int = Field(default=0, ge=0, description="Job priority (higher = more urgent)")
    timestamp: Optional[str] = Field(default=None, description="ISO 8601 timestamp")
    idempotency_key: Optional[str] = Field(default=None, description="For idempotent job processing")
    callback_url: Optional[str] = Field(default=None, description="URL for callback after processing")


# ============================================================================
# Shift Template Model
# ============================================================================

class ShiftTemplate(BaseModel):
    """Template for a shift type."""
    id: str = Field(..., description="Unique shift identifier")
    name: str = Field(..., description="Human-readable shift name")
    startTime: str = Field(..., pattern=r'^\d{2}:\d{2}$', description="Start time in HH:MM format")
    endTime: str = Field(..., pattern=r'^\d{2}:\d{2}$', description="End time in HH:MM format")
    minBreakMinutes: Optional[int] = Field(default=None, ge=0, description="Minimum break in minutes")
    skills: Optional[List[str]] = Field(default=None, description="Required skills for this shift")
    color: Optional[str] = Field(default=None, description="Color code for UI display")


# ============================================================================
# Requirement Model
# ============================================================================

class Requirement(BaseModel):
    """Shift requirement for a specific time slot."""
    # Support both old and new field names
    shiftTemplateId: Optional[str] = Field(default=None, description="Reference to shift template (new)")
    shiftId: Optional[str] = Field(default=None, alias="shiftId", description="Reference to shift template (old)")
    
    date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$', description="Date in YYYY-MM-DD format")
    startTime: Optional[str] = Field(default=None, pattern=r'^\d{2}:\d{2}$', description="Start time override")
    endTime: Optional[str] = Field(default=None, pattern=r'^\d{2}:\d{2}$', description="End time override")
    count: Optional[int] = Field(default=None, ge=1, description="Number of employees needed (new)")
    neededSkills: Optional[Dict[str, int]] = Field(default=None, description="Required skills with counts (old)")
    skills: Optional[List[str]] = Field(default=None, description="Required skills (new)")
    
    @model_validator(mode='after')
    def normalize_requirement_fields(self) -> 'Requirement':
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
    role: Optional[str] = Field(default=None, description="Primary role of the employee")
    contractHours: Optional[float] = Field(default=None, gt=0, description="Weekly contract hours (new)")
    contract: Optional[Dict[str, Any]] = Field(default=None, description="Contract details (old)")
    maxDailyHours: Optional[float] = Field(default=None, gt=0, description="Maximum daily working hours")
    skills: Optional[List[str]] = Field(default=None, description="Employee skills")
    breakMinutes: Optional[int] = Field(default=None, ge=0, description="Preferred break in minutes")
    maxConsecutiveDays: Optional[int] = Field(default=None, ge=1, le=31, description="Maximum consecutive working days")
    minFreeSundaysPerYear: Optional[int] = Field(default=None, ge=0, le=52, description="Minimum free Sundays per year")
    forbiddenDates: Optional[List[str]] = Field(default=None, description="Forbidden dates (old)")
    
    @model_validator(mode='after')
    def normalize_employee_fields(self) -> 'Employee':
        """Normalize old field names to new ones."""
        # Handle contract - extract weeklyHours if contract dict exists
        if self.contract and self.contractHours is None:
            self.contractHours = self.contract.get('weeklyHours', 40.0)
        
        return self


# ============================================================================
# Wish Models
# ============================================================================

class Wish(BaseModel):
    """Employee shift wish."""
    employeeId: str = Field(..., description="Employee ID")
    date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$', description="Date in YYYY-MM-DD format")
    shiftTemplateId: Optional[str] = Field(default=None, description="Preferred shift template (new)")
    shiftId: Optional[str] = Field(default=None, alias="shiftId", description="Preferred shift template (old)")
    type: str = Field(default="OFF", description="Wish type: OFF, SHIFT, etc.")
    priority: int = Field(default=0, ge=0, le=10, description="Wish priority (new)")
    weight: Optional[int] = Field(default=None, description="Wish weight (old)")
    comment: Optional[str] = Field(default=None, description="Comment (old)")
    
    @model_validator(mode='after')
    def normalize_wish_fields(self) -> 'Wish':
        """Normalize old field names to new ones."""
        # Handle shift ID
        if self.shiftId and not self.shiftTemplateId:
            self.shiftTemplateId = self.shiftId
        
        # Handle priority/weight
        if self.weight is not None and self.priority == 0:
            self.priority = self.weight
        
        return self


# ============================================================================
# Config Model
# ============================================================================

class Config(BaseModel):
    """Configuration for the scheduling run."""
    schemaVersion: str = Field(default="1.0", description="Schema version for backward compatibility")
    startDate: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$', description="Planning period start")
    endDate: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$', description="Planning period end")
    maxConsecutiveDays: Optional[int] = Field(default=6, ge=1, le=31, description="Max consecutive working days")
    minRestTimeHours: Optional[float] = Field(default=11, gt=0, description="Minimum rest time between shifts in hours")
    maxDailyWorkHours: Optional[float] = Field(default=10, gt=0, description="Maximum daily working hours")
    minFreeSundaysPerYear: Optional[int] = Field(default=15, ge=0, le=52, description="Minimum free Sundays per year")
    defaultWeeklyHours: Optional[float] = Field(default=40.0, gt=0, description="Default weekly contract hours")
    solverTimeoutSeconds: Optional[int] = Field(default=300, gt=0, description="Solver timeout in seconds")


# ============================================================================
# Main Job Payload Model
# ============================================================================

class JobPayload(BaseModel):
    """Main job payload with full validation."""
    model_config = ConfigDict(extra='ignore')  # Ignore unknown fields (e.g. tenant_id from backend)
    
    metadata: Metadata
    config: Config
    shiftTemplates: List[ShiftTemplate]
    requirements: List[Requirement]
    employees: List[Employee]
    wishes: Optional[List[Wish]] = Field(default=None)
    
    @model_validator(mode='after')
    def validate_references(self) -> 'JobPayload':
        """Validate that all references exist."""
        shift_ids = {st.id for st in self.shiftTemplates}
        employee_ids = {e.id for e in self.employees}
        
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
        
        return self
    
    @model_validator(mode='after')
    def validate_date_range(self) -> 'JobPayload':
        """Validate that startDate is before endDate."""
        from datetime import datetime
        
        start = datetime.strptime(self.config.startDate, "%Y-%m-%d")
        end = datetime.strptime(self.config.endDate, "%Y-%m-%d")
        
        if start >= end:
            raise ValueError("startDate must be before endDate")
        
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
    except Exception as e:
        raise ValueError(f"Validation failed: {e}")


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


class SolverStatus:
    """Solver status constants."""
    SUCCESS = "SUCCESS"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    TIMEOUT = "TIMEOUT"


class SolveResult(BaseModel):
    """Result of the optimization run."""
    status: str = Field(..., description="Solver status (SUCCESS, FEASIBLE, INFEASIBLE, TIMEOUT)")
    assignments: List[Assignment] = Field(default_factory=list, description="Schedule assignments")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Optimization metrics")
    constraintViolations: Optional[List[Dict[str, Any]]] = Field(
        default=None, 
        description="Details about constraint violations (if any)"
    )
    solverInfo: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Solver-specific information (runtime, iterations, etc.)"
    )


class JobResult(BaseModel):
    """Complete job result with metadata."""
    jobId: str
    tenantId: int
    status: str
    result: SolveResult
    createdAt: str
