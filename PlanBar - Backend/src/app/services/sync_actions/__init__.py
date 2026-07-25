from app.services.sync_actions.create_shift_wish import CreateShiftWish
from app.services.sync_actions.delete_shift_wish import DeleteShiftWish
from app.services.sync_actions.registry import SyncActionRegistry
from app.services.sync_actions.update_schedule import UpdateSchedule
from app.services.sync_actions.update_shift import UpdateShift
from app.services.sync_actions.update_shift_wish import UpdateShiftWish

for _a in (CreateShiftWish, UpdateShiftWish, DeleteShiftWish, UpdateSchedule, UpdateShift):
    SyncActionRegistry.register(_a)

__all__ = [
    "CreateShiftWish",
    "DeleteShiftWish",
    "SyncActionRegistry",
    "UpdateSchedule",
    "UpdateShift",
    "UpdateShiftWish",
]
