from pydantic import BaseModel


class MyShiftResponse(BaseModel):
    id: int
    schedule_id: int
    schedule_name: str
    employee_id: int
    date: str
    start_time: str
    end_time: str
    week: str | None = None
    break_start: str | None = None
    break_end: str | None = None
    label: str | None = None

    model_config = {"from_attributes": True}


class MyOvertimeResponse(BaseModel):
    current_balance: float = 0.0
    scheduled_hours: float = 0.0
    contract_hours: float = 0.0
    week: int | None = None
    year: int | None = None
