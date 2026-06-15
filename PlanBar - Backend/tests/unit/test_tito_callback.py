from datetime import date, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.employee import Contract, Employee, Timecard
from app.db.models.schedule import Schedule, Shiftplan
from app.services.schedule_service import _get_week_type
from app.services.tito_callback import process_tito_callback, update_timecards_from_schedule


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


def test_update_timecards_from_schedule_creates_timecards(db_session):
    emp = Employee(first_name="Test", last_name="User")
    db_session.add(emp)
    db_session.commit()
    contract = Contract(employee_id=emp.id, weekly_working_hours=40, break_time=30)
    db_session.add(contract)
    db_session.commit()

    schedule = Schedule(name="Test", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7), status="completed")
    db_session.add(schedule)
    db_session.commit()

    sp1 = Shiftplan(schedule_id=schedule.id, employee_id=emp.id, date=date(2026, 6, 1), shift_id="früh",
                    start_time=time(6, 0), end_time=time(14, 0))
    sp2 = Shiftplan(schedule_id=schedule.id, employee_id=emp.id, date=date(2026, 6, 2), shift_id="spät",
                    start_time=time(14, 0), end_time=time(22, 0))
    db_session.add_all([sp1, sp2])
    db_session.commit()

    update_timecards_from_schedule(db_session, schedule)

    timecards = db_session.query(Timecard).filter(Timecard.employee_id == emp.id).all()
    assert len(timecards) == 1
    tc = timecards[0]
    # Each 8h shift - 30min contract break = 7.5h effective, two shifts = 15h
    assert tc.scheduled_hours == 15.0
    assert tc.contract_hours == 40.0
    assert tc.balance == -25.0


def test_update_timecards_from_schedule_with_break(db_session):
    emp = Employee(first_name="Break", last_name="Test")
    db_session.add(emp)
    db_session.commit()
    contract = Contract(employee_id=emp.id, weekly_working_hours=40, break_time=45)
    db_session.add(contract)
    db_session.commit()

    schedule = Schedule(name="Break Test", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7), status="completed")
    db_session.add(schedule)
    db_session.commit()

    sp = Shiftplan(schedule_id=schedule.id, employee_id=emp.id, date=date(2026, 6, 1), shift_id="früh",
                   start_time=time(6, 0), end_time=time(14, 0), break_start="12:00", break_end="12:45")
    db_session.add(sp)
    db_session.commit()

    update_timecards_from_schedule(db_session, schedule)

    timecards = db_session.query(Timecard).all()
    assert len(timecards) == 1
    tc = timecards[0]
    assert tc.scheduled_hours == 7.25


def test_update_timecards_from_schedule_updates_existing(db_session):
    emp = Employee(first_name="Update", last_name="Test")
    db_session.add(emp)
    db_session.commit()
    contract = Contract(employee_id=emp.id, weekly_working_hours=35, break_time=30)
    db_session.add(contract)
    db_session.commit()

    existing_tc = Timecard(employee_id=emp.id, week=23, year=2026, balance=10.0)
    db_session.add(existing_tc)
    db_session.commit()

    schedule = Schedule(name="Update Test", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7), status="completed")
    db_session.add(schedule)
    db_session.commit()

    sp = Shiftplan(schedule_id=schedule.id, employee_id=emp.id, date=date(2026, 6, 1), shift_id="früh",
                   start_time=time(6, 0), end_time=time(14, 0))
    db_session.add(sp)
    db_session.commit()

    update_timecards_from_schedule(db_session, schedule)

    timecards = db_session.query(Timecard).filter(Timecard.employee_id == emp.id).all()
    assert len(timecards) == 1
    tc = timecards[0]
    # 1 shift × 7.5h effective = 7.5h, 7.5 - 35 = -27.5, prev balance 10, new = -17.5
    assert tc.balance == -17.5


def test_update_timecards_from_schedule_no_contract_defaults(db_session):
    emp = Employee(first_name="NoContract", last_name="Test")
    db_session.add(emp)
    db_session.commit()

    schedule = Schedule(name="No Contract", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7), status="completed")
    db_session.add(schedule)
    db_session.commit()

    sp = Shiftplan(schedule_id=schedule.id, employee_id=emp.id, date=date(2026, 6, 1), shift_id="früh",
                   start_time=time(6, 0), end_time=time(14, 0))
    db_session.add(sp)
    db_session.commit()

    update_timecards_from_schedule(db_session, schedule)

    timecards = db_session.query(Timecard).all()
    assert len(timecards) == 1
    tc = timecards[0]
    assert tc.scheduled_hours == 7.5
    assert tc.contract_hours == 40.0


def test_process_tito_callback_week_per_date(db_session):
    """process_tito_callback muss week pro assignment_date berechnen (nicht schedule.week_type)."""
    from app.schemas.tito import TiTOCallbackPayload, TiTOAssignment, TiTOMetadata, TiTOSolution, TiTOMetrics, TiTODiagnostics

    emp = Employee(first_name="Test", last_name="User")
    db_session.add(emp)
    db_session.commit()

    schedule = Schedule(
        name="Week Test",
        week_type=None,
        status="submitted",
        tito_job_id=42,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 14),
    )
    db_session.add(schedule)
    db_session.commit()

    payload = TiTOCallbackPayload(
        job_id=42,
        status="SUCCESS",
        metadata=TiTOMetadata(status="success", solveTimeSeconds=1.0, timestamp="2026-06-01T12:00:00"),
        solution=TiTOSolution(
            assignments=[
                TiTOAssignment(employeeId=f"emp_{emp.id:03d}", date=date(2026, 6, 1), shiftId="morning", startTime="08:00", endTime="16:00"),
                TiTOAssignment(employeeId=f"emp_{emp.id:03d}", date=date(2026, 6, 8), shiftId="evening", startTime="14:00", endTime="22:00"),
            ],
            unassignedRequirements=[],
        ),
        metrics=TiTOMetrics(wishFulfillmentRate=1.0, totalObjectiveScore=100.0, employeeUtilization={}, violations=None),
        diagnostics=TiTODiagnostics(isOptimal=True, info="Optimal"),
    )

    result = process_tito_callback(db_session, payload)
    assert result is not None

    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).order_by(Shiftplan.date).all()
    assert len(shiftplans) == 2

    assert shiftplans[0].week == _get_week_type(date(2026, 6, 1)), f"Expected A for June 1, got {shiftplans[0].week}"
    assert shiftplans[1].week == _get_week_type(date(2026, 6, 8)), f"Expected B for June 8, got {shiftplans[1].week}"
