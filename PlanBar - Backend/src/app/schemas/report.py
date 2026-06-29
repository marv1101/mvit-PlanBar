from datetime import date
from typing import Optional

from pydantic import BaseModel


class OvertimeEmployeeEntry(BaseModel):
    employee_id: int
    employee_name: str
    total_scheduled_hours: float
    total_actual_hours: float
    total_contract_hours: float
    overtime_hours: float


class OvertimeReportResponse(BaseModel):
    employees: list[OvertimeEmployeeEntry]
    summary: dict


class ComplianceViolation(BaseModel):
    rule: str
    message: str
    employee_id: int
    employee_name: str
    shift_date: str
    severity: str
    details: dict


class ComplianceReportResponse(BaseModel):
    violations: list[ComplianceViolation]
    summary: dict


class ReportFilterParams(BaseModel):
    employee_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
