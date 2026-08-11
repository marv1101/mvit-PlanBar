from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    week_type = Column(String(1), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    role_requirements = Column(JSON, nullable=True)
    shift_templates = Column(JSON, nullable=True)
    tito_job_id = Column(Integer, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    metrics_json = Column(JSON, nullable=True)
    diagnostics_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    shiftplans = relationship(
        "Shiftplan",
        back_populates="schedule",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class Shiftplan(Base):
    __tablename__ = "shiftplans"
    __table_args__ = (
        UniqueConstraint(
            "schedule_id",
            "employee_id",
            "date",
            "shift_id",
            name="uq_shiftplan_schedule_employee_date_shift",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    shift_id = Column(String(50), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    week = Column(String(1), nullable=True)
    break_start = Column(String(5), nullable=True)
    break_end = Column(String(5), nullable=True)
    label = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    metrics_json = Column(JSON, nullable=True)
    diagnostics_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    schedule = relationship("Schedule", back_populates="shiftplans")
