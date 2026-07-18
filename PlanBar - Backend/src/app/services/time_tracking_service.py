"""Time-tracking service (Issue #29 - Digitale Zeiterfassung)."""

from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.employee import Employee
from app.db.models.time_tracking import TimeEntry


def _get_employee(db: Session, employee_id: int) -> Employee:
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise ValueError(f"Employee not found: {employee_id}")
    return emp


# Re-export under the alias used by the tests
get_employee_by_id = _get_employee


def _get_open_entry(db: Session, employee_id: int) -> Optional[TimeEntry]:
    stmt = (
        select(TimeEntry)
        .where(TimeEntry.employee_id == employee_id)
        .where(TimeEntry.clock_out.is_(None))
        .order_by(TimeEntry.clock_in.desc())
    )
    return db.execute(stmt).scalars().first()


def clock_in(db: Session, employee_id: int, notes: Optional[str] = None) -> TimeEntry:
    _get_employee(db, employee_id)
    if _get_open_entry(db, employee_id) is not None:
        raise ValueError(f"Employee {employee_id} is already clocked in")
    entry = TimeEntry(
        employee_id=employee_id,
        clock_in=datetime.now(timezone.utc),
        notes=notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def clock_out(db: Session, employee_id: int) -> TimeEntry:
    _get_employee(db, employee_id)
    entry = _get_open_entry(db, employee_id)
    if entry is None:
        raise ValueError(f"No open time entry for employee {employee_id}")
    now = datetime.now(timezone.utc)
    entry.clock_out = now
    # SQLAlchemy/SQLite may strip tzinfo on roundtrip — re-attach if needed
    clock_in_ts = entry.clock_in
    if clock_in_ts.tzinfo is None:
        clock_in_ts = clock_in_ts.replace(tzinfo=timezone.utc)
    delta = (now - clock_in_ts).total_seconds() / 60.0
    entry.duration_minutes = int(round(delta))
    db.commit()
    db.refresh(entry)
    return entry


def get_daily_entries(db: Session, employee_id: int, target_date: date) -> List[TimeEntry]:
    _get_employee(db, employee_id)
    # Match by the calendar date of clock_in (UTC). This is the natural
    # definition of "entries for day X" — any shift whose start date
    # equals the requested date, regardless of exact clock-in time.
    target_start = datetime.combine(target_date, datetime.min.time())
    next_day = target_date + _one_day()
    target_end = datetime.combine(next_day, datetime.min.time())
    stmt = (
        select(TimeEntry)
        .where(TimeEntry.employee_id == employee_id)
        .where(TimeEntry.clock_in >= target_start)
        .where(TimeEntry.clock_in < target_end)
        .order_by(TimeEntry.clock_in.asc())
    )
    return list(db.execute(stmt).scalars().all())


def _one_day():
    from datetime import timedelta

    return timedelta(days=1)
