from datetime import date, datetime, time, timezone

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Time
from sqlalchemy.orm import relationship

from app.db.base import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    week_type = Column(String(1), nullable=True)
    tito_job_id = Column(Integer, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    metrics_json = Column(JSON, nullable=True)
    diagnostics_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    shiftplans = relationship("Shiftplan", back_populates="schedule", lazy="selectin", cascade="all, delete-orphan")


class Shiftplan(Base):
    __tablename__ = "shiftplans"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    shift_id = Column(String(20), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    metrics_json = Column(JSON, nullable=True)
    diagnostics_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    schedule = relationship("Schedule", back_populates="shiftplans")
