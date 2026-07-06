from typing import Optional

from pydantic import BaseModel


class MyShiftResponse(BaseModel):
    id: int
    schedule_id: int
    schedule_name: str
    date: str
    start_time: str
    end_time: str
    week: Optional[str] = None
    break_start: Optional[str] = None
    break_end: Optional[str] = None
    label: Optional[str] = None

    model_config = {"from_attributes": True}


class MyOvertimeResponse(BaseModel):
    current_balance: float = 0.0
    scheduled_hours: float = 0.0
    contract_hours: float = 0.0
    week: Optional[int] = None
    year: Optional[int] = None
