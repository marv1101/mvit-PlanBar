from enum import StrEnum


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"
    PLANNER = "planer"


class ScheduleStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class WishType(StrEnum):
    PREFERRED = "preferred"
    UNAVAILABLE = "unavailable"


class WishStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WeekType(StrEnum):
    A = "A"
    B = "B"


class NotificationType(StrEnum):
    WISH_APPROVED = "wish_approved"
    WISH_REJECTED = "wish_rejected"
    SCHEDULE_PUBLISHED = "schedule_published"
    SHIFT_CHANGED = "shift_changed"


class PushDeviceType(StrEnum):
    WEB = "web"
    MOBILE = "mobile"
    SWAP_REQUESTED = "swap_requested"
    SWAP_APPROVED = "swap_approved"
    SWAP_REJECTED = "swap_rejected"


class ShiftSwapStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
