from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base

employee_roles = Table(
    "employee_roles",
    Base.metadata,
    Column("employee_id", Integer, ForeignKey("employees.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)


# NOTE: employee_teams is defined in app.db.models.team to avoid circular imports.
# It is imported lazily via the secondary relationship below.


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    processing_restricted = Column(Boolean, default=False, nullable=False)
    first_name = Column(String(64), nullable=False)
    last_name = Column(String(64), nullable=False)
    email = Column(String(120), nullable=True)
    color = Column(String(7), nullable=True)
    working_hours_json = Column(Text, nullable=True)
    break_start = Column(String(5), nullable=True)
    break_end = Column(String(5), nullable=True)
    max_work_hours = Column(Float, nullable=True)
    # ArbZG / JArbSchG / MuSchG relevant flags (validated by app.services.arbzg_validator)
    is_minor = Column(Boolean, default=False, nullable=False)  # JArbSchG rules apply
    is_night_worker = Column(Boolean, default=False, nullable=False)  # § 6 ArbZG
    night_worker_exam_date = Column(Date, nullable=True)  # § 6 Abs. 1 Eignungsuntersuchung
    protection_until = Column(Date, nullable=True)  # MuSchG protection period end
    is_shift_worker = Column(Boolean, default=False, nullable=False)  # § 4 Abs. 2 / § 6 shift worker
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", foreign_keys=[user_id], backref="employees", lazy="selectin")
    contracts = relationship("Contract", back_populates="employee", lazy="selectin")
    timecards = relationship("Timecard", back_populates="employee", lazy="selectin")
    shift_wishes = relationship("ShiftWish", back_populates="employee", lazy="selectin")
    roles = relationship("Role", secondary=employee_roles, lazy="selectin")
    teams = relationship(
        "Team",
        secondary="employee_teams",
        lazy="selectin",
        back_populates="employees",
    )

    @property
    def team_ids(self) -> list[int]:
        return [team.id for team in self.teams]

    @property
    def role_ids(self) -> list[int]:
        return [role.id for role in self.roles]


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    weekly_working_hours = Column(Float, nullable=False)
    break_time = Column(Integer, nullable=False, default=30)
    hired_role = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    employee = relationship("Employee", back_populates="contracts")


class Timecard(Base):
    __tablename__ = "timecards"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    week = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    balance = Column(Float, nullable=False, default=0.0)
    scheduled_hours = Column(Float, default=0.0)
    actual_hours = Column(Float, default=0.0)
    contract_hours = Column(Float, default=0.0)
    manual_adjustment_hours = Column(Float, default=0.0)
    adjustment_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    employee = relationship("Employee", back_populates="timecards")
    __table_args__ = (UniqueConstraint("employee_id", "week", "year", name="uq_timecard_employee_week_year"),)
