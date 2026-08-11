from app.schemas.availability import (
    AvailabilityEntry,
    AvailabilityResponse,
    AvailabilityUpdate,
)
from app.schemas.common import ErrorResponse, PaginationResponse
from app.schemas.employee import (
    ContractCreate,
    ContractResponse,
    ContractUpdate,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    TimecardCreate,
    TimecardResponse,
    TimecardUpdate,
)
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleResponse,
    ScheduleSummary,
    ScheduleUpdate,
    ShiftplanCreate,
    ShiftplanResponse,
    ShiftplanUpdate,
)
from app.schemas.self_service import MyOvertimeResponse, MyShiftResponse
from app.schemas.shift_swap import (
    ShiftSwapCreate,
    ShiftSwapReject,
    ShiftSwapResponse,
    ShiftSwapUpdate,
)
from app.schemas.tito import TiTOCallbackPayload, TiTOJobResponse, TiTOJobStatus
from app.schemas.user import (
    TokenRefreshRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)

__all__ = [
    "AvailabilityEntry",
    "AvailabilityResponse",
    "AvailabilityUpdate",
    "ContractCreate",
    "ContractResponse",
    "ContractUpdate",
    "EmployeeCreate",
    "EmployeeResponse",
    "EmployeeUpdate",
    "ErrorResponse",
    "MyOvertimeResponse",
    "MyShiftResponse",
    "PaginationResponse",
    "ScheduleCreate",
    "ScheduleResponse",
    "ScheduleSummary",
    "ScheduleUpdate",
    "ShiftSwapCreate",
    "ShiftSwapReject",
    "ShiftSwapResponse",
    "ShiftSwapUpdate",
    "ShiftplanCreate",
    "ShiftplanResponse",
    "ShiftplanUpdate",
    "TiTOCallbackPayload",
    "TiTOJobResponse",
    "TiTOJobStatus",
    "TimecardCreate",
    "TimecardResponse",
    "TimecardUpdate",
    "TokenRefreshRequest",
    "TokenResponse",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserUpdate",
]
