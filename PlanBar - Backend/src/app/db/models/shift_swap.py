from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class ShiftSwapRequest(Base):
    __tablename__ = "shift_swap_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    requester_shift_id = Column(Integer, ForeignKey("shiftplans.id"), nullable=False)
    target_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    target_shift_id = Column(Integer, ForeignKey("shiftplans.id"), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    note = Column(Text, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    employee = relationship("Employee", foreign_keys=[employee_id])
    target_employee = relationship("Employee", foreign_keys=[target_employee_id])
    requester_shift = relationship("Shiftplan", foreign_keys=[requester_shift_id])
    target_shift = relationship("Shiftplan", foreign_keys=[target_shift_id])
