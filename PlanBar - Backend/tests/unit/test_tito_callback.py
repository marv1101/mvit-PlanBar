from datetime import date, time

import pytest
from app.db.base import Base
from app.db.models.employee import Contract, Employee, Timecard
from app.db.models.schedule import Schedule, Shiftplan
from app.schemas.tito import (
    TiTOAssignment,
    TiTOCallbackPayload,
    TiTODiagnostics,
    TiTOMetadata,
    TiTOMetrics,
    TiTOSolution,
)
from app.services.schedule_service import _get_week_type
from app.services.tito_callback import (
    CallbackConflictError,
    _aggregate_violations,
    _calc_effective_hours,
    _normalize_break,
    process_tito_callback,
    update_timecards_from_schedule,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


def _make_employee(db, first="Test", last="User", **kwargs) -> Employee:
    emp = Employee(first_name=first, last_name=last, **kwargs)
    db.add(emp)
    db.commit()
    return emp


def _make_schedule(db, job_id=42, status="submitted", start=date(2026, 6, 1), end=date(2026, 6, 7)) -> Schedule:
    schedule = Schedule(name="Test", status=status, tito_job_id=job_id, start_date=start, end_date=end)
    db.add(schedule)
    db.commit()
    return schedule


def _assignment_payload(employee_id, d="2026-06-01", start="08:00", end="16:00", shift="morning", break_minutes=30):
    if isinstance(d, date):
        d = d.isoformat()
    return {
        "employeeId": employee_id,
        "date": d,
        "shiftId": shift,
        "startTime": start,
        "endTime": end,
        "breakMinutes": break_minutes,
        "name": "",
    }


def _callback_payload(
    job_id,
    status="SUCCESS",
    assignments=None,
    violations=None,
    error=None,
    attempts=None,
) -> TiTOCallbackPayload:
    """Build a contract-v2 (flat) callback payload."""
    data = {
        "job_id": job_id,
        "status": status,
        "assignments": assignments or [],
        "unassignedRequirements": [],
        "violations": violations or [],
        "metrics": {
            "wishFulfillmentRate": 1.0,
            "totalObjectiveScore": 100.0,
            "employeeUtilization": {},
            "employeeFairness": 0.9,
        },
        "diagnostics": {"isOptimal": True, "info": "Optimal"},
    }
    if error is not None:
        data["error"] = error
    if attempts is not None:
        data["attempts"] = attempts
    return TiTOCallbackPayload.model_validate(data)


def test_update_timecards_from_schedule_creates_timecards(db_session):
    emp = Employee(first_name="Test", last_name="User")
    db_session.add(emp)
    db_session.commit()
    contract = Contract(employee_id=emp.id, weekly_working_hours=40, break_time=30)
    db_session.add(contract)
    db_session.commit()

    schedule = Schedule(
        name="Test",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="completed",
    )
    db_session.add(schedule)
    db_session.commit()

    sp1 = Shiftplan(
        schedule_id=schedule.id,
        employee_id=emp.id,
        date=date(2026, 6, 1),
        shift_id="früh",
        start_time=time(6, 0),
        end_time=time(14, 0),
    )
    sp2 = Shiftplan(
        schedule_id=schedule.id,
        employee_id=emp.id,
        date=date(2026, 6, 2),
        shift_id="spät",
        start_time=time(14, 0),
        end_time=time(22, 0),
    )
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

    schedule = Schedule(
        name="Break Test",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="completed",
    )
    db_session.add(schedule)
    db_session.commit()

    sp = Shiftplan(
        schedule_id=schedule.id,
        employee_id=emp.id,
        date=date(2026, 6, 1),
        shift_id="früh",
        start_time=time(6, 0),
        end_time=time(14, 0),
        break_start="12:00",
        break_end="12:45",
    )
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

    schedule = Schedule(
        name="Update Test",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="completed",
    )
    db_session.add(schedule)
    db_session.commit()

    sp = Shiftplan(
        schedule_id=schedule.id,
        employee_id=emp.id,
        date=date(2026, 6, 1),
        shift_id="früh",
        start_time=time(6, 0),
        end_time=time(14, 0),
    )
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

    schedule = Schedule(
        name="No Contract",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="completed",
    )
    db_session.add(schedule)
    db_session.commit()

    sp = Shiftplan(
        schedule_id=schedule.id,
        employee_id=emp.id,
        date=date(2026, 6, 1),
        shift_id="früh",
        start_time=time(6, 0),
        end_time=time(14, 0),
    )
    db_session.add(sp)
    db_session.commit()

    update_timecards_from_schedule(db_session, schedule)

    timecards = db_session.query(Timecard).all()
    assert len(timecards) == 1
    tc = timecards[0]
    assert tc.scheduled_hours == 7.5
    assert tc.contract_hours == 40.0


def test_update_timecards_additive_across_schedules(db_session):
    """C4c: scheduled_hours per week must sum over ALL schedules, not overwrite."""
    emp = _make_employee(db_session)
    contract = Contract(employee_id=emp.id, weekly_working_hours=40, break_time=30)
    db_session.add(contract)
    db_session.commit()

    sched_a = Schedule(name="A", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7), status="completed")
    db_session.add(sched_a)
    db_session.commit()
    db_session.add(
        Shiftplan(
            schedule_id=sched_a.id,
            employee_id=emp.id,
            date=date(2026, 6, 1),
            shift_id="früh",
            start_time=time(6, 0),
            end_time=time(14, 0),
        )
    )
    db_session.commit()

    # First callback for schedule A: 7.5h
    update_timecards_from_schedule(db_session, sched_a)
    tc = db_session.query(Timecard).filter(Timecard.employee_id == emp.id).one()
    assert tc.scheduled_hours == 7.5

    # Later callback for schedule B in the same week: must ADD (7.5 + 7.5 = 15h)
    sched_b = Schedule(name="B", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7), status="completed")
    db_session.add(sched_b)
    db_session.commit()
    db_session.add(
        Shiftplan(
            schedule_id=sched_b.id,
            employee_id=emp.id,
            date=date(2026, 6, 2),
            shift_id="früh",
            start_time=time(6, 0),
            end_time=time(14, 0),
        )
    )
    db_session.commit()

    update_timecards_from_schedule(db_session, sched_b)
    db_session.refresh(tc)
    assert tc.scheduled_hours == 15.0


def test_process_tito_callback_week_per_date(db_session):
    """process_tito_callback muss week pro assignment_date berechnen (nicht schedule.week_type)."""
    emp = _make_employee(db_session)
    schedule = _make_schedule(db_session, job_id=42, start=date(2026, 6, 1), end=date(2026, 6, 14))

    payload = _callback_payload(
        42,
        assignments=[
            _assignment_payload(emp.id, "2026-06-01", "08:00", "16:00"),
            _assignment_payload(emp.id, "2026-06-08", "14:00", "22:00", shift="evening"),
        ],
    )

    result = process_tito_callback(db_session, payload)
    assert result is not None

    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).order_by(Shiftplan.date).all()
    assert len(shiftplans) == 2

    assert shiftplans[0].week == _get_week_type(date(2026, 6, 1)), f"Expected A for June 1, got {shiftplans[0].week}"
    assert shiftplans[1].week == _get_week_type(date(2026, 6, 8)), f"Expected B for June 8, got {shiftplans[1].week}"


def test_process_tito_callback_legacy_nested_payload(db_session):
    """Übergangsweise wird auch das alte verschachtelte Payload-Format akzeptiert."""
    emp = _make_employee(db_session)
    schedule = _make_schedule(db_session, job_id=43)

    payload = TiTOCallbackPayload(
        job_id=43,
        status="SUCCESS",
        metadata=TiTOMetadata(status="success", solveTimeSeconds=1.0, timestamp="2026-06-01T12:00:00"),
        solution=TiTOSolution(
            assignments=[
                TiTOAssignment(
                    employeeId=f"emp_{emp.id:03d}",
                    date=date(2026, 6, 1),
                    shiftId="morning",
                    startTime="08:00",
                    endTime="16:00",
                ),
            ],
            unassignedRequirements=[],
        ),
        metrics=TiTOMetrics(wishFulfillmentRate=1.0, totalObjectiveScore=100.0, employeeUtilization={}),
        diagnostics=TiTODiagnostics(isOptimal=True, info="Optimal"),
    )

    result = process_tito_callback(db_session, payload)
    assert result is not None
    assert result.status == "completed"
    assert db_session.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).count() == 1


def test_process_tito_callback_job_id_alias(db_session):
    """C6: 'jobId' (camelCase) muss als Alias für job_id akzeptiert werden."""
    emp = _make_employee(db_session)
    _make_schedule(db_session, job_id=77)

    payload = TiTOCallbackPayload.model_validate(
        {
            "jobId": 77,
            "status": "SUCCESS",
            "assignments": [_assignment_payload(emp.id)],
        }
    )
    assert payload.job_id == 77
    result = process_tito_callback(db_session, payload)
    assert result is not None
    assert result.status == "completed"


# ── A2: status mapping ──────────────────────────────────────────────────────
def test_timeout_writes_no_data_marks_failed(db_session):
    """A2: TIMEOUT muss 'failed' setzen und KEINE Shiftplans/Timecards schreiben."""
    emp = _make_employee(db_session)
    schedule = _make_schedule(db_session, job_id=50)

    # Draft shiftplan as working basis (manually planned)
    draft = Shiftplan(
        schedule_id=schedule.id,
        employee_id=emp.id,
        date=date(2026, 6, 2),
        shift_id="draft",
        start_time=time(8, 0),
        end_time=time(16, 0),
    )
    db_session.add(draft)
    db_session.commit()

    payload = _callback_payload(
        50,
        status="TIMEOUT",
        assignments=[_assignment_payload(emp.id, "2026-06-03")],  # non-empty: old bug wrote this
    )
    result = process_tito_callback(db_session, payload)

    assert result.status == "failed"
    # Draft shiftplan bleibt als Arbeitsgrundlage erhalten, nichts Neues geschrieben
    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).all()
    assert len(shiftplans) == 1
    assert shiftplans[0].shift_id == "draft"
    assert db_session.query(Timecard).count() == 0


def test_infeasible_marks_failed_without_writes(db_session):
    schedule = _make_schedule(db_session, job_id=51)
    payload = _callback_payload(51, status="INFEASIBLE")
    result = process_tito_callback(db_session, payload)
    assert result.status == "failed"
    assert db_session.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).count() == 0


def test_failed_error_callback_persists_error(db_session):
    """A2/Contract v2: FAILED-Fehlercallback persistiert error + attempts."""
    _make_schedule(db_session, job_id=52)
    payload = _callback_payload(52, status="FAILED", error="solver crashed", attempts=3)
    result = process_tito_callback(db_session, payload)

    assert result.status == "failed"
    assert result.diagnostics_json["error"] == "solver crashed"
    assert result.diagnostics_json["attempts"] == 3


def test_unknown_status_raises_validation_error():
    """Unbekannter Status ist ein Schemafehler (422), kein stillschweigendes Übernehmen."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TiTOCallbackPayload.model_validate({"job_id": 1, "status": "WHATEVER"})


# ── A1: scope + validation ──────────────────────────────────────────────────
def test_out_of_scope_assignment_discarded_with_violation(db_session):
    """A1: assignment.date außerhalb [start_date, end_date] → verwerfen + OUT_OF_SCOPE."""
    emp = _make_employee(db_session)
    schedule = _make_schedule(db_session, job_id=53, start=date(2026, 6, 1), end=date(2026, 6, 7))

    payload = _callback_payload(
        53,
        assignments=[
            _assignment_payload(emp.id, "2026-06-03"),  # in scope
            _assignment_payload(emp.id, "2026-06-20"),  # OUT of scope
        ],
    )
    result = process_tito_callback(db_session, payload)

    assert result.status == "completed"
    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).all()
    assert len(shiftplans) == 1
    assert shiftplans[0].date == date(2026, 6, 3)

    callback_violations = result.diagnostics_json["callbackViolations"]
    assert len(callback_violations) == 1
    assert callback_violations[0]["rule"] == "OUT_OF_SCOPE"
    assert callback_violations[0]["date"] == "2026-06-20"


def test_hard_arbzg_violation_rejects_whole_solution(db_session):
    """A1: HARD-Verstoß (12h ohne Pause) → Status 'failed', Shiftplans werden NICHT neu geschrieben."""
    emp = _make_employee(db_session)
    schedule = _make_schedule(db_session, job_id=54)

    draft = Shiftplan(
        schedule_id=schedule.id,
        employee_id=emp.id,
        date=date(2026, 6, 2),
        shift_id="draft",
        start_time=time(8, 0),
        end_time=time(16, 0),
    )
    db_session.add(draft)
    db_session.commit()

    payload = _callback_payload(
        54,
        assignments=[_assignment_payload(emp.id, "2026-06-03", "06:00", "18:00", break_minutes=0)],  # 12h netto
    )
    result = process_tito_callback(db_session, payload)

    assert result.status == "failed"
    # Bestehende Draft-Shiftplans bleiben erhalten, keine neuen geschrieben
    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).all()
    assert len(shiftplans) == 1
    assert shiftplans[0].shift_id == "draft"

    arbzg = result.diagnostics_json["arbZgViolations"]
    assert any(v["severity"] == "HARD" for v in arbzg)


def test_soft_arbzg_violation_accepted_and_persisted(db_session):
    """A1: Nur SOFT-Verstöße (Sonntagsarbeit im Kurzzeitraum) → übernehmen + Violations persistieren."""
    emp = _make_employee(db_session)
    schedule = _make_schedule(db_session, job_id=55, start=date(2026, 6, 1), end=date(2026, 6, 7))

    payload = _callback_payload(
        55,
        assignments=[_assignment_payload(emp.id, "2026-06-07")],  # Sunday
    )
    result = process_tito_callback(db_session, payload)

    assert result.status == "completed"
    assert db_session.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).count() == 1
    arbzg = result.diagnostics_json["arbZgViolations"]
    assert any(v["rule"] == "sunday_quota" and v["severity"] == "SOFT" for v in arbzg)


# ── A4: robust parsing ──────────────────────────────────────────────────────
def test_invalid_employee_id_skipped_with_violation(db_session):
    """A4: unparsebare employeeId → Assignment überspringen + INVALID_ASSIGNMENT (kein 500)."""
    emp = _make_employee(db_session)
    schedule = _make_schedule(db_session, job_id=56)

    payload = _callback_payload(
        56,
        assignments=[
            _assignment_payload("emp_abc", "2026-06-03"),
            _assignment_payload(emp.id, "2026-06-04"),
        ],
    )
    result = process_tito_callback(db_session, payload)

    assert result.status == "completed"
    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).all()
    assert len(shiftplans) == 1
    assert shiftplans[0].employee_id == emp.id

    callback_violations = result.diagnostics_json["callbackViolations"]
    assert len(callback_violations) == 1
    assert callback_violations[0]["rule"] == "INVALID_ASSIGNMENT"


def test_unknown_employee_id_skipped_with_violation(db_session):
    _make_schedule(db_session, job_id=57)
    payload = _callback_payload(57, assignments=[_assignment_payload(9999, "2026-06-03")])
    result = process_tito_callback(db_session, payload)

    assert result.status == "completed"
    assert db_session.query(Shiftplan).count() == 0
    assert result.diagnostics_json["callbackViolations"][0]["rule"] == "INVALID_ASSIGNMENT"


def test_malformed_times_skipped_with_violation(db_session):
    """A4: malformed startTime/endTime → Assignment überspringen + Violation."""
    emp = _make_employee(db_session)
    _make_schedule(db_session, job_id=58)

    payload = _callback_payload(
        58,
        assignments=[
            _assignment_payload(emp.id, "2026-06-03", start="8 Uhr"),
            _assignment_payload(emp.id, "2026-06-04", end="25:99"),
        ],
    )
    result = process_tito_callback(db_session, payload)

    assert result.status == "completed"
    assert db_session.query(Shiftplan).count() == 0
    violations = result.diagnostics_json["callbackViolations"]
    assert len(violations) == 2
    assert all(v["rule"] == "INVALID_ASSIGNMENT" for v in violations)


# ── A4: break normalization ─────────────────────────────────────────────────
def test_normalize_break_keeps_valid_employee_window():
    """A4: Mitarbeiter-Pause im Schichtfenster wird unverändert übernommen."""
    emp = Employee(first_name="B", last_name="W", break_start="12:00", break_end="12:30")
    bs, be, minutes = _normalize_break(time(8, 0), time(16, 0), emp, None, 30)
    assert (bs, be, minutes) == ("12:00", "12:30", 30)


def test_normalize_break_rejects_outside_window():
    """A4: Pause außerhalb des Schichtfensters wird durch Mitte-der-Schicht-Default ersetzt."""
    emp = Employee(first_name="B", last_name="O", break_start="12:00", break_end="12:30")
    # Shift 14:00-22:00: 12:00-12:30 liegt NICHT im Fenster → Default Mitte (18:00), 15-min-gerundet
    bs, be, minutes = _normalize_break(time(14, 0), time(22, 0), emp, None, 30)
    assert bs == "17:45" and be == "18:15" and minutes == 30


def test_normalize_break_uses_assignment_break_minutes():
    emp = Employee(first_name="B", last_name="A")  # no employee window
    bs, be, minutes = _normalize_break(time(8, 0), time(16, 0), emp, None, 45)
    assert minutes == 45
    assert be > bs  # positioned inside the shift


def test_normalize_break_uses_contract_break_time():
    emp = Employee(first_name="B", last_name="C")
    contract = Contract(employee_id=1, weekly_working_hours=40, break_time=45)
    bs, be, minutes = _normalize_break(time(8, 0), time(16, 0), emp, contract, 0)
    assert minutes == 45
    start_min = int(bs[:2]) * 60 + int(bs[3:])
    end_min = int(be[:2]) * 60 + int(be[3:])
    assert end_min - start_min == 45


def test_normalize_break_statutory_default_via_shared_rules():
    """B1: ohne explizite Pause-Angaben gilt § 4 (via arbzg_rules, >6h statt >=6h)."""
    from datetime import time as time_cls

    emp = Employee(first_name="B", last_name="S")
    # exactly 6h shift: no statutory break
    bs, be, minutes = _normalize_break(time_cls(8, 0), time_cls(14, 0), emp, None, 0)
    assert (bs, be, minutes) == (None, None, 0)
    # 8h shift: 30 min statutory default
    bs, be, minutes = _normalize_break(time_cls(8, 0), time_cls(16, 0), emp, None, 0)
    assert minutes == 30


def test_normalize_break_overnight_shift():
    """Pause in einer Nachtschicht (22:00-06:00) wird im Schichtfenster platziert."""
    emp = Employee(first_name="B", last_name="N", break_start="12:00", break_end="12:30")  # invalid for night
    bs, be, minutes = _normalize_break(time(22, 0), time(6, 0), emp, None, 30)
    assert minutes == 30
    bs_min = int(bs[:2]) * 60 + int(bs[3:])
    be_min = int(be[:2]) * 60 + int(be[3:])
    if bs_min < 22 * 60:  # break in the next-day part of the overnight shift
        bs_min += 24 * 60
    if be_min <= bs_min:
        be_min += 24 * 60
    assert 22 * 60 <= bs_min and be_min <= 30 * 60  # within 22:00-06:00(+1d)


# ── B1: shared constants in effective hours ─────────────────────────────────
def test_calc_effective_hours_uses_shared_break_rules():
    """B1: gesetzliche Pause aus arbzg_rules (>6h statt >=6h)."""
    sp = Shiftplan(
        schedule_id=1,
        employee_id=1,
        date=date(2026, 6, 1),
        shift_id="x",
        start_time=time(8, 0),
        end_time=time(14, 0),  # exactly 6h -> no statutory break
    )
    assert _calc_effective_hours(sp, None) == 6.0

    sp.start_time = time(8, 0)
    sp.end_time = time(17, 0)  # 9h -> 30 min (not 45: only >9h needs 45)
    assert _calc_effective_hours(sp, None) == 8.5

    sp.end_time = time(17, 30)  # 9.5h -> 45 min
    assert _calc_effective_hours(sp, None) == 8.75


# ── A3: state machine ───────────────────────────────────────────────────────
def test_idempotent_second_callback_no_rewrite(db_session):
    """A3: zweiter identischer Callback (Schedule bereits 'completed') → idempotent, kein erneutes Schreiben."""
    emp = _make_employee(db_session)
    schedule = _make_schedule(db_session, job_id=60)

    payload = _callback_payload(60, assignments=[_assignment_payload(emp.id, "2026-06-03")])
    first = process_tito_callback(db_session, payload)
    assert first.status == "completed"

    # Someone manually edited the shiftplan afterwards
    sp = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).one()
    sp.label = "manuell geändert"
    db_session.commit()

    second = process_tito_callback(db_session, payload)
    assert second.status == "completed"
    db_session.refresh(sp)
    assert sp.label == "manuell geändert"  # not overwritten
    assert db_session.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).count() == 1


def test_conflict_when_schedule_not_submitted(db_session):
    """A3: Callback für Schedule im Status 'draft' → CallbackConflictError (→ 409)."""
    _make_schedule(db_session, job_id=61, status="draft")
    payload = _callback_payload(61)
    with pytest.raises(CallbackConflictError):
        process_tito_callback(db_session, payload)


def test_conflict_when_schedule_completed_with_other_state(db_session):
    """A3: 'failed'-Status (terminal verarbeitet) → idempotent OK statt Endlos-Retry."""
    _make_schedule(db_session, job_id=62, status="failed")
    payload = _callback_payload(62, status="INFEASIBLE")
    result = process_tito_callback(db_session, payload)
    assert result.status == "failed"


def test_callback_unknown_job_returns_none(db_session):
    payload = _callback_payload(9999)
    assert process_tito_callback(db_session, payload) is None


# ── aggregated violations (unassigned requirements) ─────────────────────────
def _hard_violation(skill, shift_id, d, count=1):
    return {
        "type": "UNASSIGNED_REQUIREMENT",
        "severity": "HARD",
        "message": "...",
        "details": {"date": d, "count": count, "skills": [skill], "shiftId": shift_id, "shiftTemplateId": shift_id},
    }


def test_aggregate_violations_no_violations(db_session):
    schedule = Schedule(name="Test", start_date=date(2026, 6, 15), end_date=date(2026, 7, 12))
    db_session.add(schedule)
    db_session.commit()

    payload = _callback_payload(job_id=1, status="INFEASIBLE", violations=[])
    result = _aggregate_violations(schedule, payload)
    assert result == []


def test_aggregate_violations_groups_by_skill(db_session):
    schedule = Schedule(
        name="Test",
        start_date=date(2026, 6, 15),
        end_date=date(2026, 7, 12),
        shift_templates=[
            {"id": "frueh", "name": "Frühschicht", "startTime": "06:00", "endTime": "14:00"},
            {"id": "spaet", "name": "Spätschicht", "startTime": "14:00", "endTime": "22:00"},
        ],
    )
    db_session.add(schedule)
    db_session.commit()

    violations = [
        _hard_violation("Apotheker", "frueh", "2026-06-15"),
        _hard_violation("Apotheker", "spaet", "2026-06-15"),
        _hard_violation("PKA", "frueh", "2026-06-15"),
        _hard_violation("Apotheker", "frueh", "2026-06-16"),
    ]
    payload = _callback_payload(job_id=1, status="INFEASIBLE", violations=violations)
    result = _aggregate_violations(schedule, payload)

    assert len(result) == 2

    apo = next(m for m in result if m["skill"] == "Apotheker")
    assert apo["totalMissingShifts"] == 3
    assert apo["totalMissingHours"] == 24  # 3×8h
    assert apo["affectedDays"] == 2
    assert "24" in apo["message"]
    assert "Apotheker" in apo["message"]

    pka = next(m for m in result if m["skill"] == "PKA")
    assert pka["totalMissingShifts"] == 1
    assert pka["totalMissingHours"] == 8
    assert pka["affectedDays"] == 1


def test_aggregate_violations_skips_non_hard(db_session):
    schedule = Schedule(name="Test", start_date=date(2026, 6, 15), end_date=date(2026, 7, 12))
    db_session.add(schedule)
    db_session.commit()

    violations = [
        {"type": "WISH_NOT_FULFILLED", "severity": "SOFT", "message": "...", "details": {}},
        _hard_violation("Apotheker", "s1", "2026-06-15"),
    ]
    payload = _callback_payload(job_id=1, status="INFEASIBLE", violations=violations)
    result = _aggregate_violations(schedule, payload)
    assert len(result) == 1
    assert result[0]["skill"] == "Apotheker"


def test_aggregate_violations_fallback_duration_without_templates(db_session):
    schedule = Schedule(name="Test", start_date=date(2026, 6, 15), end_date=date(2026, 7, 12))
    db_session.add(schedule)
    db_session.commit()

    payload = _callback_payload(
        job_id=1, status="INFEASIBLE", violations=[_hard_violation("Apotheker", "x", "2026-06-15")]
    )
    result = _aggregate_violations(schedule, payload)
    assert result[0]["totalMissingHours"] == 8  # default 8h fallback


def test_aggregate_violations_from_legacy_metrics(db_session):
    """Übergangskompatibilität: violations aus metrics.violations werden ebenfalls aggregiert."""
    schedule = Schedule(name="Test", start_date=date(2026, 6, 15), end_date=date(2026, 7, 12))
    db_session.add(schedule)
    db_session.commit()

    payload = TiTOCallbackPayload(
        job_id=1,
        status="INFEASIBLE",
        metadata=TiTOMetadata(status="infeasible", solveTimeSeconds=0.1, timestamp="2026-06-15T12:00:00"),
        solution=TiTOSolution(assignments=[], unassignedRequirements=[]),
        metrics=TiTOMetrics(
            wishFulfillmentRate=0.0,
            totalObjectiveScore=0.0,
            employeeUtilization={},
            violations=[_hard_violation("Apotheker", "frueh", "2026-06-15")],
        ),
        diagnostics=TiTODiagnostics(isOptimal=False, info="Keine Lösung gefunden."),
    )
    result = _aggregate_violations(schedule, payload)
    assert len(result) == 1
    assert result[0]["skill"] == "Apotheker"


def test_aggregate_violations_stored_in_process_callback(db_session):
    schedule = Schedule(
        name="Aggregation Test",
        status="submitted",
        tito_job_id=99,
        start_date=date(2026, 6, 15),
        end_date=date(2026, 7, 12),
        shift_templates=[{"id": "frueh", "name": "Frühschicht", "startTime": "06:00", "endTime": "14:00"}],
    )
    db_session.add(schedule)
    db_session.commit()

    payload = _callback_payload(
        99,
        status="INFEASIBLE",
        violations=[_hard_violation("Apotheker", "frueh", "2026-06-15")],
    )

    result = process_tito_callback(db_session, payload)
    assert result is not None
    assert result.status == "failed"
    assert result.diagnostics_json is not None
    assert "aggregatedMessages" in result.diagnostics_json
    assert len(result.diagnostics_json["aggregatedMessages"]) == 1
    assert result.diagnostics_json["aggregatedMessages"][0]["skill"] == "Apotheker"
