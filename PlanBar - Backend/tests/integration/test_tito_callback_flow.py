"""Integration tests for TiTO callback flow (callback contract v2)."""

from datetime import date, time
from unittest.mock import AsyncMock, patch

import pytest
from app.db.models.employee import Contract, Employee, Timecard
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.shift_wish import ShiftWish
from app.services.schedule_service import submit_schedule_to_tito
from sqlalchemy.orm import Session


@pytest.fixture
def test_schedule(db_session: Session) -> Schedule:
    """Create a test schedule without shiftplans."""
    schedule = Schedule(
        name="Test Schedule",
        week_type="A",
        status="draft",
        start_date=date(2026, 5, 24),
        end_date=date(2026, 5, 30),
        role_requirements={"früh": "1"},
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)
    return schedule


@pytest.fixture
def test_employee(db_session: Session) -> Employee:
    """Create a test employee."""
    employee = Employee(
        first_name="John",
        last_name="Doe",
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)
    return employee


@pytest.fixture
def test_employees_two(db_session: Session) -> dict[str, Employee]:
    """Create two test employees (emp_001 and emp_002)."""
    emp1 = Employee(first_name="Alice", last_name="Smith")
    emp2 = Employee(first_name="Bob", last_name="Jones")
    db_session.add_all([emp1, emp2])
    db_session.commit()
    db_session.refresh(emp1)
    db_session.refresh(emp2)
    return {"001": emp1, "002": emp2}


@pytest.fixture(autouse=True)
def _dev_environment():
    """Ensure callback processing tests run in development mode (no auth required)."""
    from app.config import settings

    original = settings.environment
    settings.environment = "development"
    yield
    settings.environment = original


@pytest.fixture
def test_shift_wish(db_session: Session, test_employee: Employee) -> ShiftWish:
    """Create a test shift wish (approved, so it doesn't block TiTO submission)."""
    db_session.query(ShiftWish).delete()
    db_session.commit()
    wish = ShiftWish(
        employee_id=test_employee.id,
        date=date(2026, 5, 24),
        type="preferred",
        note="Morning shift preferred",
        status="approved",
    )
    db_session.add(wish)
    db_session.commit()
    db_session.refresh(wish)
    return wish


def _assignment(employee, d="2026-05-24", shift="morning", start="08:00", end="16:00", break_minutes=30):
    """Build an assignment dict per callback contract v2 (employeeId: int)."""
    emp_id = employee.id if hasattr(employee, "id") else employee
    return {
        "employeeId": emp_id,
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
):
    """Build a flat contract-v2 callback payload."""
    payload = {
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
        "diagnostics": {"isOptimal": True, "info": "Solution is optimal"},
    }
    if error is not None:
        payload["error"] = error
    if attempts is not None:
        payload["attempts"] = attempts
    return payload


@pytest.mark.asyncio
async def test_submit_schedule_includes_callback_url(
    db_session: Session,
    test_schedule: Schedule,
    test_employee: Employee,
    test_shift_wish: ShiftWish,
):
    """Test that submitted job includes callback_url in metadata (without api_key)."""
    mock_response = {"jobId": 123, "status": "queued"}

    with patch("app.services.tito_proxy.tito_proxy.submit_job", new_callable=AsyncMock) as mock_submit:
        mock_submit.return_value = mock_response

        result = await submit_schedule_to_tito(db_session, test_schedule)

        # Verify the job was submitted
        assert result.status == "submitted"
        assert result.tito_job_id == 123

        # Verify submit_job was called
        mock_submit.assert_called_once()

        # Get the actual payload that was sent
        call_args = mock_submit.call_args
        payload = call_args[0][0]

        # Verify metadata is included with callback_url
        assert "metadata" in payload
        assert "callback_url" in payload["metadata"]
        assert "callbacks/tito" in payload["metadata"]["callback_url"]
        # C7: API-Key darf NICHT mehr in der URL stehen (Bearer-Header statt Query-Param)
        assert "api_key" not in payload["metadata"]["callback_url"]
        # C1: versionierter Idempotency-Key
        assert "idempotency_key" in payload["metadata"]
        assert f"schedule_{test_schedule.id}_1" == payload["metadata"]["idempotency_key"]


def test_callback_endpoint_processes_results(
    client,
    db_session: Session,
    test_schedule: Schedule,
    test_employees_two: dict[str, Employee],
):
    """Test that callback endpoint correctly updates schedule."""
    alice = test_employees_two["001"]
    test_schedule.status = "submitted"
    test_schedule.tito_job_id = 125
    db_session.add(test_schedule)
    db_session.commit()

    response = client.post(
        "/api/v1/callbacks/tito",
        json=_callback_payload(125, assignments=[_assignment(alice)]),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "processed"

    # Verify schedule was updated
    db_session.refresh(test_schedule)
    assert test_schedule.status == "completed"
    assert test_schedule.metadata_json is not None
    assert test_schedule.metrics_json is not None
    assert test_schedule.diagnostics_json is not None

    # Verify new shiftplan was created from solution
    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == test_schedule.id).all()
    assert len(shiftplans) == 1
    assert shiftplans[0].employee_id == alice.id
    assert shiftplans[0].shift_id == "morning"


def test_duplicate_callback_does_not_create_duplicate_shiftplans(
    client,
    db_session: Session,
    test_schedule: Schedule,
    test_employees_two: dict[str, Employee],
):
    """Simulate receiving the same callback twice (e.g., due to retry or idempotency logic)."""
    alice = test_employees_two["001"]
    test_schedule.status = "submitted"
    test_schedule.tito_job_id = 128
    db_session.add(test_schedule)
    db_session.commit()

    payload = _callback_payload(128, assignments=[_assignment(alice)])

    # First callback
    response1 = client.post("/api/v1/callbacks/tito", json=payload)
    assert response1.status_code == 200

    # Second callback (same payload - simulates retry/duplicate) → idempotent 200
    response2 = client.post("/api/v1/callbacks/tito", json=payload)
    assert response2.status_code == 200

    # Verify only ONE shiftplan exists (not two)
    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == test_schedule.id).all()
    assert len(shiftplans) == 1, f"Expected 1 shiftplan, got {len(shiftplans)}"
    assert shiftplans[0].employee_id == alice.id
    assert shiftplans[0].shift_id == "morning"


def test_callback_endpoint_with_feasible_status(
    client,
    db_session: Session,
    test_schedule: Schedule,
    test_employees_two: dict[str, Employee],
):
    """Test that FEASIBLE solver status is treated as completed."""
    alice = test_employees_two["001"]
    bob = test_employees_two["002"]
    test_schedule.status = "submitted"
    test_schedule.tito_job_id = 127
    db_session.add(test_schedule)
    db_session.commit()

    payload = _callback_payload(
        127,
        status="FEASIBLE",
        assignments=[
            _assignment(alice),
            _assignment(bob, shift="evening", start="16:00", end="23:00"),
        ],
    )

    response = client.post("/api/v1/callbacks/tito", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "processed"

    # Verify schedule was marked as completed despite FEASIBLE status
    db_session.refresh(test_schedule)
    assert test_schedule.status == "completed"

    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == test_schedule.id).all()
    assert len(shiftplans) == 2


def test_callback_endpoint_with_legacy_completed_status(
    client,
    db_session: Session,
    test_schedule: Schedule,
    test_employees_two: dict[str, Employee],
):
    """Legacy status 'completed' is still accepted and treated as success."""
    alice = test_employees_two["001"]
    bob = test_employees_two["002"]
    test_schedule.status = "submitted"
    test_schedule.tito_job_id = 126
    db_session.add(test_schedule)
    db_session.commit()

    payload = _callback_payload(
        126,
        status="completed",
        assignments=[
            _assignment(alice),
            _assignment(bob, shift="evening", start="16:00", end="23:00"),
        ],
    )

    response = client.post("/api/v1/callbacks/tito", json=payload)
    assert response.status_code == 200

    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == test_schedule.id).all()
    assert len(shiftplans) == 2
    assert {sp.employee_id for sp in shiftplans} == {alice.id, bob.id}


def test_callback_multiweek_schedule_balance_chaining(client, db_session: Session, test_employee: Employee):
    """Test that balance chains correctly across multiple weeks in one schedule."""
    contract = Contract(employee_id=test_employee.id, weekly_working_hours=40.0, break_time=30)
    db_session.add(contract)
    db_session.commit()

    schedule = Schedule(
        name="Multi-Week Test",
        week_type="A",
        status="submitted",
        start_date=date(2026, 5, 25),
        end_date=date(2026, 6, 7),
        tito_job_id=200,
    )
    db_session.add(schedule)
    db_session.commit()

    assignments = [
        # ISO week 22: 2026-05-25 (Mon) to 2026-05-31 (Sun)
        *[_assignment(test_employee, f"2026-05-{25 + i}") for i in range(4)],
        # ISO week 23: 2026-06-01 (Mon) to 2026-06-07 (Sun)
        *[_assignment(test_employee, f"2026-06-0{i + 1}") for i in range(4)],
    ]

    response = client.post("/api/v1/callbacks/tito", json=_callback_payload(200, assignments=assignments))
    assert response.status_code == 200

    timecards = (
        db_session.query(Timecard)
        .filter(Timecard.employee_id == test_employee.id)
        .order_by(Timecard.year, Timecard.week)
        .all()
    )

    assert len(timecards) == 2

    tc_w22 = timecards[0]
    assert tc_w22.scheduled_hours == 30.0
    assert tc_w22.contract_hours == 40.0
    assert tc_w22.balance == -10.0

    tc_w23 = timecards[1]
    assert tc_w23.scheduled_hours == 30.0
    assert tc_w23.contract_hours == 40.0
    assert tc_w23.balance == -20.0


def test_callback_endpoint_with_invalid_job_id(client):
    """Test callback endpoint with non-existent job id."""
    response = client.post("/api/v1/callbacks/tito", json=_callback_payload(999))

    # Should return 404 (no schedule for this job)
    assert response.status_code == 404


def test_callback_clears_manual_adjustment_on_reschedule(client, db_session: Session, test_employee: Employee):
    """When a callback updates a timecard that has manual_adjustment_hours (from an
    earlier adjustment that was applied on top of schedule data), the manual_adjustment_hours
    and adjustment_reason should be cleared because the balance is recalculated.
    """
    emp = test_employee
    contract = Contract(employee_id=emp.id, weekly_working_hours=40.0, break_time=30)
    db_session.add(contract)
    db_session.commit()

    tc = Timecard(
        employee_id=emp.id,
        week=21,
        year=2026,
        scheduled_hours=38.0,
        contract_hours=40.0,
        manual_adjustment_hours=5.0,
        adjustment_reason="Korrektur",
        balance=3.0,
    )
    db_session.add(tc)
    db_session.commit()

    schedule = Schedule(
        name="Reschedule",
        start_date=date(2026, 5, 18),
        end_date=date(2026, 5, 24),
        status="submitted",
        tito_job_id=300,
    )
    db_session.add(schedule)
    db_session.commit()

    assignments = [_assignment(emp, f"2026-05-{18 + i}") for i in range(5)]

    response = client.post("/api/v1/callbacks/tito", json=_callback_payload(300, assignments=assignments))
    assert response.status_code == 200

    updated_tc = (
        db_session.query(Timecard)
        .filter(Timecard.employee_id == emp.id, Timecard.week == 21, Timecard.year == 2026)
        .first()
    )

    assert updated_tc is not None
    assert updated_tc.scheduled_hours == 37.5
    assert updated_tc.contract_hours == 40.0
    assert updated_tc.manual_adjustment_hours == 0.0
    assert updated_tc.adjustment_reason is None


# --- A1/A2/A3/A4: callback processing behaviour (contract v2) ---


def test_callback_timeout_marks_failed_and_writes_no_data(
    client,
    db_session: Session,
    test_schedule: Schedule,
    test_employee: Employee,
):
    """A2: TIMEOUT → 'failed', keine Shiftplans/Timecards, Draft bleibt Arbeitsgrundlage."""
    test_schedule.status = "submitted"
    test_schedule.tito_job_id = 310
    db_session.commit()

    draft = Shiftplan(
        schedule_id=test_schedule.id,
        employee_id=test_employee.id,
        date=date(2026, 5, 26),
        shift_id="draft",
        start_time=time(8, 0),
        end_time=time(16, 0),
    )
    db_session.add(draft)
    db_session.commit()

    response = client.post(
        "/api/v1/callbacks/tito",
        json=_callback_payload(310, status="TIMEOUT", assignments=[_assignment(test_employee, "2026-05-27")]),
    )
    assert response.status_code == 200

    db_session.refresh(test_schedule)
    assert test_schedule.status == "failed"
    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == test_schedule.id).all()
    assert len(shiftplans) == 1
    assert shiftplans[0].shift_id == "draft"
    assert db_session.query(Timecard).filter(Timecard.employee_id == test_employee.id).count() == 0


def test_callback_failed_persists_error(
    client,
    db_session: Session,
    test_schedule: Schedule,
):
    """A2/contract v2: FAILED-Fehlercallback mit error + attempts."""
    test_schedule.status = "submitted"
    test_schedule.tito_job_id = 311
    db_session.commit()

    response = client.post(
        "/api/v1/callbacks/tito",
        json=_callback_payload(311, status="FAILED", error="solver crashed", attempts=2),
    )
    assert response.status_code == 200

    db_session.refresh(test_schedule)
    assert test_schedule.status == "failed"
    assert test_schedule.diagnostics_json["error"] == "solver crashed"
    assert test_schedule.diagnostics_json["attempts"] == 2


def test_callback_out_of_scope_assignment_discarded(
    client,
    db_session: Session,
    test_schedule: Schedule,
    test_employee: Employee,
):
    """A1: Assignment außerhalb des Planungszeitraums wird verworfen (OUT_OF_SCOPE)."""
    test_schedule.status = "submitted"
    test_schedule.tito_job_id = 312
    db_session.commit()

    response = client.post(
        "/api/v1/callbacks/tito",
        json=_callback_payload(
            312,
            assignments=[
                _assignment(test_employee, "2026-05-26"),
                _assignment(test_employee, "2026-06-20"),  # außerhalb 24.-30.05.
            ],
        ),
    )
    assert response.status_code == 200

    db_session.refresh(test_schedule)
    assert test_schedule.status == "completed"
    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == test_schedule.id).all()
    assert len(shiftplans) == 1
    assert shiftplans[0].date == date(2026, 5, 26)
    assert any(v["rule"] == "OUT_OF_SCOPE" for v in test_schedule.diagnostics_json["callbackViolations"])


def test_callback_malformed_assignment_no_500(
    client,
    db_session: Session,
    test_schedule: Schedule,
    test_employee: Employee,
):
    """A4: malformed Assignments → 200 + violations, kein 500/Retry-Loop."""
    test_schedule.status = "submitted"
    test_schedule.tito_job_id = 313
    db_session.commit()

    response = client.post(
        "/api/v1/callbacks/tito",
        json=_callback_payload(
            313,
            assignments=[
                {"employeeId": "emp_abc", "date": "2026-05-26", "shiftId": "x", "startTime": "08:00", "endTime": "16:00"},
                {"employeeId": test_employee.id, "date": "2026-05-27", "shiftId": "x", "startTime": "8 Uhr", "endTime": "16:00"},
                _assignment(test_employee, "2026-05-28"),
            ],
        ),
    )
    assert response.status_code == 200

    db_session.refresh(test_schedule)
    assert test_schedule.status == "completed"
    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == test_schedule.id).all()
    assert len(shiftplans) == 1
    assert shiftplans[0].date == date(2026, 5, 28)
    violations = test_schedule.diagnostics_json["callbackViolations"]
    assert len(violations) == 2
    assert all(v["rule"] == "INVALID_ASSIGNMENT" for v in violations)


def test_callback_hard_arbzg_violation_rejects_solution(
    client,
    db_session: Session,
    test_schedule: Schedule,
    test_employee: Employee,
):
    """A1: HARD-ArbZG-Verstoß (11h netto ohne Pause) → 'failed', keine neuen Shiftplans."""
    test_schedule.status = "submitted"
    test_schedule.tito_job_id = 314
    db_session.commit()

    draft = Shiftplan(
        schedule_id=test_schedule.id,
        employee_id=test_employee.id,
        date=date(2026, 5, 26),
        shift_id="draft",
        start_time=time(8, 0),
        end_time=time(16, 0),
    )
    db_session.add(draft)
    db_session.commit()

    response = client.post(
        "/api/v1/callbacks/tito",
        json=_callback_payload(
            314,
            assignments=[
                _assignment(test_employee, "2026-05-27", start="07:00", end="19:00", break_minutes=0),  # 12h netto
            ],
        ),
    )
    assert response.status_code == 200  # kein Retry-Loop

    db_session.refresh(test_schedule)
    assert test_schedule.status == "failed"
    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == test_schedule.id).all()
    assert len(shiftplans) == 1
    assert shiftplans[0].shift_id == "draft"  # Draft bleibt, nichts überschrieben
    assert any(v["severity"] == "HARD" for v in test_schedule.diagnostics_json["arbZgViolations"])


def test_callback_conflict_when_schedule_not_submitted(
    client,
    db_session: Session,
    test_schedule: Schedule,
):
    """A3: Schedule im Status 'draft' → 409 (TiTO hört nach 3 Versuchen auf)."""
    test_schedule.tito_job_id = 315
    test_schedule.status = "draft"
    db_session.commit()

    response = client.post("/api/v1/callbacks/tito", json=_callback_payload(315))
    assert response.status_code == 409


def test_submit_empty_requirements_rejected(client, db_session: Session, auth_headers):
    """C5: Submission ohne Requirements → 422."""
    schedule = Schedule(
        name="No Reqs",
        status="draft",
        start_date=date(2026, 5, 24),
        end_date=date(2026, 5, 30),
    )
    db_session.add(schedule)
    db_session.commit()

    response = client.post(f"/api/v1/schedules/{schedule.id}/submit", headers=auth_headers)
    assert response.status_code == 422
    assert "Requirements" in response.json()["detail"]


def test_submit_duplicate_409_from_tito_is_clean_client_error(client, db_session: Session, auth_headers):
    """C1: TiTO antwortet 409 auf den Idempotency-Key → sauberer 422 (kein 500)."""
    import httpx

    schedule = Schedule(
        name="Dup Submit",
        status="draft",
        start_date=date(2026, 5, 24),
        end_date=date(2026, 5, 30),
        role_requirements={"früh": "1"},
    )
    db_session.add(schedule)
    db_session.commit()

    request = httpx.Request("POST", "http://tito/jobs")
    response_409 = httpx.Response(409, request=request, json={"detail": "duplicate idempotency key"})
    exc = httpx.HTTPStatusError("409", request=request, response=response_409)

    with patch("app.services.tito_proxy.tito_proxy.submit_job", new_callable=AsyncMock, side_effect=exc):
        api_response = client.post(f"/api/v1/schedules/{schedule.id}/submit", headers=auth_headers)

    assert api_response.status_code == 422
    assert "bereits bei TiTO eingereicht" in api_response.json()["detail"]
    db_session.refresh(schedule)
    assert schedule.status == "draft"


# --- B5: manual PUT path blocks HARD ArbZG violations ---


def test_replace_shifts_hard_violation_returns_422(client, db_session: Session):
    """B5: HARD-Verstoß im manuellen PUT /shifts → 422 mit violations."""
    from app.db.models.user import User

    # Create admin user
    client.post(
        "/api/v1/users",
        json={"username": "admin_arbzg", "email": "admin_arbzg@test.com", "password": "TestPass@123"},
    )
    user = db_session.query(User).filter(User.email == "admin_arbzg@test.com").first()
    user.role = "admin"
    db_session.commit()
    login = client.post("/api/v1/users/login", json={"email": "admin_arbzg@test.com", "password": "TestPass@123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.cookies.clear()

    create = client.post(
        "/api/v1/schedules",
        json={
            "name": "ArbZG Block",
            "start_date": "2026-06-01",
            "end_date": "2026-06-07",
            "shiftplans": [
                {
                    "employee_id": 1,
                    "date": "2026-06-02",
                    "shift_id": "keep",
                    "start_time": "08:00:00",
                    "end_time": "16:00:00",
                    "break_start": "12:00",
                    "break_end": "12:30",
                }
            ],
        },
        headers=headers,
    )
    assert create.status_code == 201
    schedule_id = create.json()["id"]

    response = client.put(
        f"/api/v1/schedules/{schedule_id}/shifts",
        json={
            "shiftplans": [
                {
                    "employee_id": 1,
                    "date": "2026-06-03",
                    "shift_id": "früh",
                    "start_time": "06:00:00",
                    "end_time": "18:00:00",  # 12h ohne Pause → HARD
                }
            ]
        },
        headers=headers,
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "violations" in detail
    assert any(v["severity"] == "HARD" for v in detail["violations"])

    # Bestehende Shiftplans bleiben erhalten
    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == schedule_id).all()
    assert len(shiftplans) == 1
    assert shiftplans[0].shift_id == "keep"


def test_replace_shifts_soft_violation_returns_200_with_warnings(client, db_session: Session):
    """B5: Nur SOFT-Verstöße → 200, arbZgWarnings im Response."""
    from app.db.models.user import User

    client.post(
        "/api/v1/users",
        json={"username": "admin_arbzg_soft", "email": "admin_arbzg_soft@test.com", "password": "TestPass@123"},
    )
    user = db_session.query(User).filter(User.email == "admin_arbzg_soft@test.com").first()
    user.role = "admin"
    db_session.commit()
    login = client.post(
        "/api/v1/users/login", json={"email": "admin_arbzg_soft@test.com", "password": "TestPass@123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.cookies.clear()

    create = client.post(
        "/api/v1/schedules",
        json={"name": "ArbZG Soft", "start_date": "2026-06-01", "end_date": "2026-06-07"},
        headers=headers,
    )
    schedule_id = create.json()["id"]

    response = client.put(
        f"/api/v1/schedules/{schedule_id}/shifts",
        json={
            "shiftplans": [
                {
                    "employee_id": 1,
                    "date": "2026-06-07",  # Sonntag → sunday_quota SOFT
                    "shift_id": "früh",
                    "start_time": "08:00:00",
                    "end_time": "16:00:00",
                    "break_start": "12:00",
                    "break_end": "12:30",
                }
            ]
        },
        headers=headers,
    )
    assert response.status_code == 200
    warnings = response.json()["arbZgWarnings"]
    assert any(w["rule"] == "sunday_quota" for w in warnings)


# --- TiTO callback auth tests (C7) ---


def _minimal_callback_payload(job_id: int = 1) -> dict:
    """Minimal valid callback payload for auth tests."""
    return _callback_payload(job_id)


def test_callback_auth_valid_key(client, db_session, test_schedule):
    """Valid API key via Bearer header should be accepted."""
    test_schedule.tito_job_id = 500
    test_schedule.status = "submitted"
    db_session.commit()

    from app.config import settings

    original = settings.tito_api_key
    settings.tito_api_key = "secret-token-123"
    try:
        response = client.post(
            "/api/v1/callbacks/tito",
            json=_minimal_callback_payload(500),
            headers={"Authorization": "Bearer secret-token-123"},
        )
        assert response.status_code == 200
    finally:
        settings.tito_api_key = original


def test_callback_auth_valid_key_via_x_api_key_header(client, db_session, test_schedule):
    """C7: X-API-Key header is accepted as an alternative to Bearer."""
    test_schedule.tito_job_id = 501
    test_schedule.status = "submitted"
    db_session.commit()

    from app.config import settings

    original = settings.tito_api_key
    settings.tito_api_key = "secret-token-123"
    try:
        response = client.post(
            "/api/v1/callbacks/tito",
            json=_minimal_callback_payload(501),
            headers={"X-API-Key": "secret-token-123"},
        )
        assert response.status_code == 200
    finally:
        settings.tito_api_key = original


def test_callback_auth_query_param_rejected(client, db_session, test_schedule):
    """C7: api_key as query parameter is NO longer accepted."""
    test_schedule.tito_job_id = 502
    test_schedule.status = "submitted"
    db_session.commit()

    from app.config import settings

    original = settings.tito_api_key
    settings.tito_api_key = "secret-token-123"
    try:
        response = client.post(
            "/api/v1/callbacks/tito",
            json=_minimal_callback_payload(502),
            params={"api_key": "secret-token-123"},
        )
        assert response.status_code in [401, 403]
    finally:
        settings.tito_api_key = original


def test_callback_auth_invalid_key(client, test_schedule):
    """Wrong API key should return 401."""
    from app.config import settings

    original = settings.tito_api_key
    settings.tito_api_key = "real-key"
    try:
        response = client.post(
            "/api/v1/callbacks/tito",
            json=_minimal_callback_payload(1),
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert response.status_code in [401, 403]
    finally:
        settings.tito_api_key = original


def test_callback_auth_missing_header(client, test_schedule):
    """Missing Authorization header should return 401 when key is configured."""
    from app.config import settings

    original = settings.tito_api_key
    settings.tito_api_key = "some-key"
    try:
        response = client.post(
            "/api/v1/callbacks/tito",
            json=_minimal_callback_payload(1),
        )
        assert response.status_code in [401, 403]
    finally:
        settings.tito_api_key = original


def test_callback_auth_no_key_configured(client, db_session, test_schedule):
    """When tito_api_key is None in development, requests are allowed (dev fallback)."""
    from app.config import settings

    original_key = settings.tito_api_key
    original_env = settings.environment
    settings.tito_api_key = None
    settings.environment = "development"
    test_schedule.tito_job_id = 600
    test_schedule.status = "submitted"
    db_session.commit()
    try:
        response = client.post(
            "/api/v1/callbacks/tito",
            json=_minimal_callback_payload(600),
        )
        assert response.status_code == 200
    finally:
        settings.tito_api_key = original_key
        settings.environment = original_env


def test_callback_auth_no_key_rejects_in_production(client, db_session, test_schedule):
    """When tito_api_key is None in production, requests are rejected with 503."""
    from app.config import settings

    original_key = settings.tito_api_key
    original_env = settings.environment
    settings.tito_api_key = None
    settings.environment = "production"
    test_schedule.tito_job_id = 700
    test_schedule.status = "submitted"
    db_session.commit()
    try:
        response = client.post(
            "/api/v1/callbacks/tito",
            json=_minimal_callback_payload(700),
        )
        assert response.status_code == 503
    finally:
        settings.tito_api_key = original_key
        settings.environment = original_env



