"""TDD: Cross-plan ArbZG context loader (all existing plans for employees)."""

from datetime import date, time

import pytest
from app.db.models.schedule import Schedule, Shiftplan
from app.services.arbzg_cross_plan import collect_cross_plan_shifts, combine_weekly_history

P_START = date(2026, 6, 1)
P_END = date(2026, 6, 7)  # Mon..Sun


@pytest.fixture(autouse=True)
def _clean_schedules(db_session):
    db_session.query(Shiftplan).delete()
    db_session.query(Schedule).delete()
    db_session.commit()


def _make_schedule(db, name, **kw):
    s = Schedule(name=name, start_date=P_START, end_date=P_END, status="draft", **kw)
    db.add(s)
    db.commit()
    return s


def _add_shift(db, schedule, employee_id, d, start="08:00:00", end="16:00:00"):
    db.add(
        Shiftplan(
            schedule_id=schedule.id,
            employee_id=employee_id,
            date=d,
            shift_id="früh",
            start_time=time.fromisoformat(start),
            end_time=time.fromisoformat(end),
        )
    )


def test_returns_shifts_from_other_schedules_for_same_employees(db_session):
    current = _make_schedule(db_session, "current")
    other = _make_schedule(db_session, "other")
    _add_shift(db_session, other, 1, date(2026, 6, 8))
    db_session.commit()

    shifts = collect_cross_plan_shifts(db_session, current, {1})

    assert len(shifts) == 1
    assert shifts[0]["employee_id"] == 1
    assert shifts[0]["date"] == date(2026, 6, 8)
    assert shifts[0]["start_time"] == time(8, 0)
    assert shifts[0]["end_time"] == time(16, 0)


def test_excludes_shiftplans_of_the_current_schedule(db_session):
    current = _make_schedule(db_session, "current")
    _add_shift(db_session, current, 1, date(2026, 6, 2))
    db_session.commit()

    assert collect_cross_plan_shifts(db_session, current, {1}) == []


def test_excludes_employees_not_in_the_new_plan(db_session):
    current = _make_schedule(db_session, "current")
    other = _make_schedule(db_session, "other")
    _add_shift(db_session, other, 99, date(2026, 6, 8))
    db_session.commit()

    assert collect_cross_plan_shifts(db_session, current, {1}) == []


def test_filters_days_outside_the_window(db_session):
    current = _make_schedule(db_session, "current")
    other = _make_schedule(db_session, "other")
    _add_shift(db_session, other, 1, P_START)  # within window (+14 days)
    _add_shift(db_session, other, 1, date(2026, 6, 25))  # far outside
    db_session.commit()

    shifts = collect_cross_plan_shifts(db_session, current, {1})
    assert {s["date"] for s in shifts} == {P_START}


def test_empty_when_no_other_plans_exist(db_session):
    current = _make_schedule(db_session, "current")
    assert collect_cross_plan_shifts(db_session, current, {1}) == []


def test_empty_without_employee_ids(db_session):
    current = _make_schedule(db_session, "current")
    other = _make_schedule(db_session, "other")
    _add_shift(db_session, other, 1, P_START)
    db_session.commit()
    assert collect_cross_plan_shifts(db_session, current, set()) == []


def test_empty_without_schedule_period(db_session):
    schedule = Schedule(name="No Period", status="draft")
    db_session.add(schedule)
    db_session.commit()
    assert collect_cross_plan_shifts(db_session, schedule, {1}) == []


# ── combine_weekly_history (rolling average across plans) ───────────────────



def test_planned_past_weeks_added_to_history():
    cross = [{"employee_id": 1, "date": date(2026, 5, 11), "start_time": time(8, 0), "end_date": date(2026, 5, 11), "end_time": time(16, 0), "break_start": "12:00", "break_end": "12:30"}]
    history = combine_weekly_history({}, cross, date(2026, 6, 1))
    assert history == {1: [(2026, 20, 7.5)]}


def test_timecard_wins_over_planned_hours():
    cross = [{"employee_id": 1, "date": date(2026, 5, 11), "start_time": time(8, 0), "end_date": date(2026, 5, 11), "end_time": time(16, 0)}]
    history = combine_weekly_history({1: [(2026, 20, 30.0)]}, cross, date(2026, 6, 1))
    assert history == {1: [(2026, 20, 30.0)]}


def test_weeks_from_current_period_ignored():
    cross = [{"employee_id": 1, "date": date(2026, 6, 2), "start_time": time(8, 0), "end_date": date(2026, 6, 2), "end_time": time(16, 0)}]
    assert combine_weekly_history({}, cross, date(2026, 6, 1)) == {}


def test_timecard_history_kept_untouched():
    timecards = {1: [(2025, 10, 42.0)]}
    assert combine_weekly_history(timecards, [], date(2026, 6, 1)) == {1: [(2025, 10, 42.0)]}
