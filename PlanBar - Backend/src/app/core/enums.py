from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class ScheduleStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class WishType(str, Enum):
    PREFERRED = "preferred"
    UNAVAILABLE = "unavailable"


class WeekType(str, Enum):
    A = "A"
    B = "B"
