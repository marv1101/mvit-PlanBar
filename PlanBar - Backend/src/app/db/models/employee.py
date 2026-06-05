from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


employee_roles = Table(
    "employee_roles",
    Base.metadata,
    Column("employee_id", Integer, ForeignKey("employees.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    first_name = Column(String(64), nullable=False)
    last_name = Column(String(64), nullable=False)
    email = Column(String(120), nullable=True)
    color = Column(String(7), nullable=True)
    working_hours_json = Column(Text, nullable=True)
    break_start = Column(String(5), nullable=True)
    break_end = Column(String(5), nullable=True)
    max_work_hours = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", backref="employees", lazy="selectin")
    contracts = relationship("Contract", back_populates="employee", lazy="selectin")
    timecards = relationship("Timecard", back_populates="employee", lazy="selectin")
    shift_wishes = relationship("ShiftWish", back_populates="employee", lazy="selectin")
    roles = relationship("Role", secondary=employee_roles, lazy="selectin")

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
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    employee = relationship("Employee", back_populates="timecards")
    __table_args__ = (UniqueConstraint("employee_id", "week", "year", name="uq_timecard_employee_week_year"),)
