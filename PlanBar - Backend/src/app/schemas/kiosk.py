from pydantic import BaseModel


class KioskTeamItem(BaseModel):
    id: int
    name: str


class KioskEmployeeItem(BaseModel):
    id: int
    name: str
    color: str | None = None


class KioskShiftItem(BaseModel):
    employee_id: int
    date: str
    start_time: str
    end_time: str
    break_start: str | None = None
    break_end: str | None = None
    label: str | None = None
    schedule_name: str


class KioskBoardResponse(BaseModel):
    window_start: str
    window_end: str
    team: KioskTeamItem | None = None
    employees: list[KioskEmployeeItem] = []
    shifts: list[KioskShiftItem] = []
