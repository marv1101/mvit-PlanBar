"""Pydantic schemas for payroll export (Issue #31)."""
from datetime import date
from typing import List

from pydantic import BaseModel


class OvertimeWeek(BaseModel):
    year: int
    week: int
    scheduled_hours: float
    actual_hours: float
    overtime_hours: float


class OvertimeResult(BaseModel):
    employee_id: int
    start_date: date
    end_date: date
    total_scheduled_hours: float
    total_actual_hours: float
    total_overtime_hours: float
    weeks: List[OvertimeWeek]


class PayrollExportRequest(BaseModel):
    employee_id: int
    start_date: date
    end_date: date
