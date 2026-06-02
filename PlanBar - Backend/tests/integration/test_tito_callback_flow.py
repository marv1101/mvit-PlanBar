"""Integration tests for TiTO callback flow."""
from datetime import date, time
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.orm import Session

from app.db.models.employee import Employee
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.shift_wish import ShiftWish
from app.schemas.schedule import ScheduleCreate, ShiftplanCreate
from app.services.schedule_service import submit_schedule_to_tito


@pytest.fixture
def test_schedule(db_session: Session) -> Schedule:
    """Create a test schedule without shiftplans."""
    schedule = Schedule(
        name="Test Schedule",
        week_type="A",
        status="draft",
        start_date=date(2026, 5, 24),
        end_date=date(2026, 5, 30),
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


@pytest.fixture
def test_shift_wish(db_session: Session, test_employee: Employee) -> ShiftWish:
    """Create a test shift wish."""
    wish = ShiftWish(
        employee_id=test_employee.id,
        date=date(2026, 5, 24),
        type="preferred",
        note="Morning shift preferred",
    )
    db_session.add(wish)
    db_session.commit()
    db_session.refresh(wish)
    return wish


@pytest.mark.asyncio
async def test_submit_schedule_includes_callback_url(
    db_session: Session, test_schedule: Schedule, test_employee: Employee, test_shift_wish: ShiftWish
):
    """Test that submitted job includes callback_url in metadata."""
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
        assert "idempotency_key" in payload["metadata"]
        assert f"schedule_{test_schedule.id}" == payload["metadata"]["idempotency_key"]


def test_callback_endpoint_processes_results(client, db_session: Session, test_schedule: Schedule, test_employees_two: dict[str, Employee]):
    """Test that callback endpoint correctly updates schedule."""
    alice = test_employees_two["001"]
    test_schedule.status = "submitted"
    test_schedule.tito_job_id = 125
    db_session.add(test_schedule)
    db_session.commit()

    callback_payload = {
        "job_id": 125,
        "status": "SUCCESS",
        "metadata": {
            "status": "success",
            "solveTimeSeconds": 2.5,
            "timestamp": "2026-05-24T12:30:00",
        },
        "solution": {
            "assignments": [
                {
                    "employeeId": f"emp_{alice.id:03d}",
                    "date": "2026-05-24",
                    "shiftId": "morning",
                    "startTime": "08:00",
                    "endTime": "16:00",
                }
            ],
            "unassignedRequirements": [],
        },
        "metrics": {
            "wishFulfillmentRate": 0.95,
            "totalObjectiveScore": 850.5,
            "employeeUtilization": {f"emp_{alice.id:03d}": 0.95},
            "violations": None,
        },
        "diagnostics": {
            "isOptimal": True,
            "info": "Solution is optimal",
        },
    }

    response = client.post("/api/v1/callbacks/tito", json=callback_payload)

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


def test_duplicate_callback_does_not_create_duplicate_shiftplans(client, db_session: Session, test_schedule: Schedule, test_employees_two: dict[str, Employee]):
    """Simulate receiving the same callback twice (e.g., due to retry or idempotency logic)."""
    alice = test_employees_two["001"]
    test_schedule.status = "submitted"
    test_schedule.tito_job_id = 128
    db_session.add(test_schedule)
    db_session.commit()

    callback_payload = {
        "job_id": 128,
        "status": "SUCCESS",
        "metadata": {"status": "success", "solveTimeSeconds": 1.0, "timestamp": "2026-05-24T12:30:00"},
        "solution": {
            "assignments": [
                {
                    "employeeId": f"emp_{alice.id:03d}",
                    "date": "2026-05-24",
                    "shiftId": "morning",
                    "startTime": "08:00",
                    "endTime": "16:00",
                }
            ],
            "unassignedRequirements": [],
        },
        "metrics": {"wishFulfillmentRate": 1.0, "totalObjectiveScore": 100.0, "employeeUtilization": {f"emp_{alice.id:03d}": 1.0}, "violations": None},
        "diagnostics": {"isOptimal": True, "info": "Solution is optimal"},
    }

    # First callback
    response1 = client.post("/api/v1/callbacks/tito", json=callback_payload)
    assert response1.status_code == 200

    # Second callback (same payload - simulates retry/duplicate)
    response2 = client.post("/api/v1/callbacks/tito", json=callback_payload)
    assert response2.status_code == 200

    # Verify only ONE shiftplan exists (not two)
    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == test_schedule.id).all()
    assert len(shiftplans) == 1, f"Expected 1 shiftplan, got {len(shiftplans)}"
    assert shiftplans[0].employee_id == alice.id
    assert shiftplans[0].shift_id == "morning"


def test_callback_endpoint_with_feasible_status(client, db_session: Session, test_schedule: Schedule, test_employees_two: dict[str, Employee]):
    """Test that FEASIBLE solver status is treated as completed."""
    alice = test_employees_two["001"]
    bob = test_employees_two["002"]
    test_schedule.status = "submitted"
    test_schedule.tito_job_id = 127
    db_session.add(test_schedule)
    db_session.commit()

    callback_payload = {
        "job_id": 127,
        "status": "FEASIBLE",
        "metadata": {
            "status": "feasible",
            "solveTimeSeconds": 5.0,
            "timestamp": "2026-05-24T12:40:00",
        },
        "solution": {
            "assignments": [
                {
                    "employeeId": f"emp_{alice.id:03d}",
                    "date": "2026-05-24",
                    "shiftId": "morning",
                    "startTime": "08:00",
                    "endTime": "16:00",
                },
                {
                    "employeeId": f"emp_{bob.id:03d}",
                    "date": "2026-05-24",
                    "shiftId": "evening",
                    "startTime": "16:00",
                    "endTime": "23:00",
                },
            ],
            "unassignedRequirements": [],
        },
        "metrics": {
            "wishFulfillmentRate": 0.85,
            "totalObjectiveScore": 750.0,
            "employeeUtilization": {f"emp_{alice.id:03d}": 0.90, f"emp_{bob.id:03d}": 0.80},
            "violations": None,
        },
        "diagnostics": {
            "isOptimal": False,
            "info": "Feasible solution found (not optimal)",
        },
    }

    response = client.post("/api/v1/callbacks/tito", json=callback_payload)

    assert response.status_code == 200
    assert response.json()["status"] == "processed"

    # Verify schedule was marked as completed despite FEASIBLE status
    db_session.refresh(test_schedule)
    assert test_schedule.status == "completed"

    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == test_schedule.id).all()
    assert len(shiftplans) == 2


def test_callback_endpoint_with_multiple_assignments(client, db_session: Session, test_schedule: Schedule, test_employees_two: dict[str, Employee]):
    """Test callback with multiple employee assignments."""
    alice = test_employees_two["001"]
    bob = test_employees_two["002"]
    test_schedule.status = "submitted"
    test_schedule.tito_job_id = 126
    db_session.add(test_schedule)
    db_session.commit()

    callback_payload = {
        "job_id": 126,
        "status": "completed",
        "metadata": {
            "status": "success",
            "solveTimeSeconds": 3.2,
            "timestamp": "2026-05-24T12:35:00",
        },
        "solution": {
            "assignments": [
                {
                    "employeeId": f"emp_{alice.id:03d}",
                    "date": "2026-05-24",
                    "shiftId": "morning",
                    "startTime": "08:00",
                    "endTime": "16:00",
                },
                {
                    "employeeId": f"emp_{bob.id:03d}",
                    "date": "2026-05-24",
                    "shiftId": "evening",
                    "startTime": "16:00",
                    "endTime": "23:00",
                },
            ],
            "unassignedRequirements": [],
        },
        "metrics": {
            "wishFulfillmentRate": 0.98,
            "totalObjectiveScore": 920.3,
            "employeeUtilization": {f"emp_{alice.id:03d}": 0.95, f"emp_{bob.id:03d}": 0.88},
            "violations": None,
        },
        "diagnostics": {
            "isOptimal": True,
            "info": "Optimal solution found",
        },
    }

    response = client.post("/api/v1/callbacks/tito", json=callback_payload)

    assert response.status_code == 200

    # Verify multiple shiftplans were created
    shiftplans = db_session.query(Shiftplan).filter(Shiftplan.schedule_id == test_schedule.id).all()
    assert len(shiftplans) == 2
    assert {sp.employee_id for sp in shiftplans} == {alice.id, bob.id}


def test_callback_endpoint_with_invalid_job_id(client):
    """Test callback endpoint with non-existent job id."""
    callback_payload = {
        "job_id": 999,
        "status": "completed",
        "metadata": {
            "status": "success",
            "solveTimeSeconds": 1.0,
            "timestamp": "2026-05-24T12:40:00",
        },
        "solution": {
            "assignments": [],
            "unassignedRequirements": [],
        },
        "metrics": {
            "wishFulfillmentRate": 0.0,
            "totalObjectiveScore": 0.0,
            "employeeUtilization": {},
            "violations": None,
        },
        "diagnostics": {
            "isOptimal": False,
            "info": "No valid solution",
        },
    }

    response = client.post("/api/v1/callbacks/tito", json=callback_payload)

    # Should return error or 404
    assert response.status_code in [404, 400, 500]
