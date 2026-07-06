from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class ScheduleStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class WishType(str, Enum):
    PREFERRED = "preferred"
    UNAVAILABLE = "unavailable"


class WishStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WeekType(str, Enum):
    A = "A"
    B = "B"


class NotificationType(str, Enum):
    WISH_APPROVED = "wish_approved"
    WISH_REJECTED = "wish_rejected"
    SCHEDULE_PUBLISHED = "schedule_published"
    SHIFT_CHANGED = "shift_changed"


class PushDeviceType(str, Enum):
    WEB = "web"
    MOBILE = "mobile"
    SWAP_REQUESTED = "swap_requested"
    SWAP_APPROVED = "swap_approved"
    SWAP_REJECTED = "swap_rejected"


class ShiftSwapStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
