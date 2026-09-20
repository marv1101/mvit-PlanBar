"""Cross-plan ArbZG validation context.

Collects planned shifts of the relevant employees from ALL existing
schedules (except the one being validated). Weeks that are not yet planned
contribute no shifts and are therefore treated as compliant
("Rahmenbedingungen assumed"); they simply don't block the new plan.

These shifts extend the ArbZG rule checks across plan boundaries
(§ 5 rest time, § 3 + § 9 consecutive days, § 3 weekly hours): a HARD
violation is only flagged when at least one involved shift belongs to the
plan currently being validated.
"""

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.schedule import Schedule, Shiftplan
from app.services.arbzg_validator import _shift_net_hours

CROSS_PLAN_WINDOW_DAYS = 14


def collect_cross_plan_shifts(
    db: Session,
    schedule: Schedule,
    employee_ids: set[int],
) -> list[dict[str, Any]]:
    """Shifts of ``employee_ids`` from all other plans within the window."""
    if not employee_ids or not schedule.start_date or not schedule.end_date:
        return []
    window_start = schedule.start_date - timedelta(days=CROSS_PLAN_WINDOW_DAYS)
    window_end = schedule.end_date + timedelta(days=CROSS_PLAN_WINDOW_DAYS)
    rows = (
        db.query(Shiftplan)
        .filter(
            Shiftplan.employee_id.in_(employee_ids),
            Shiftplan.schedule_id != schedule.id,
            Shiftplan.date >= window_start,
            Shiftplan.date <= window_end,
        )
        .all()
    )
    return [
        {
            "employee_id": sp.employee_id,
            "date": sp.date,
            "start_time": sp.start_time,
            "end_date": sp.date,
            "end_time": sp.end_time,
            "break_start": sp.break_start,
            "break_end": sp.break_end,
        }
        for sp in rows
    ]


def combine_weekly_history(
    timecard_history: dict[int, list[tuple[int, int, float]]],
    cross_plan_shifts: list[dict[str, Any]],
    period_start: date,
) -> dict[int, list[tuple[int, int, float]]]:
    """Extend the Timecard history with planned hours from other plans.

    Only weeks strictly before ``period_start`` are considered. Weeks that
    are NOT yet planned anywhere stay absent (assumed valid); weeks already
    covered by a Timecard keep the Timecard value.
    """
    planned: dict[tuple[int, int, int], float] = defaultdict(float)
    if period_start is not None:
        period_key = period_start.isocalendar()[:2]
        for s in cross_plan_shifts:
            d = s.get("date")
            if isinstance(d, str):
                d = date.fromisoformat(d)
            if d is None:
                continue
            eid = s.get("employee_id")
            year, week = d.isocalendar()[:2]
            if (year, week) < period_key:
                planned[(eid, year, week)] += _shift_net_hours(s)

    extended = {eid: list(weeks) for eid, weeks in timecard_history.items()}
    existing = {(eid, y, w) for eid, weeks in timecard_history.items() for y, w, _ in weeks}
    for (eid, year, week), hours in planned.items():
        if (eid, year, week) not in existing:
            extended.setdefault(eid, []).append((year, week, hours))
    for weeks in extended.values():
        weeks.sort()
    return extended
