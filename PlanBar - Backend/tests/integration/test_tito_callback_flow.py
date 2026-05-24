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
    """Create a test schedule with shiftplans."""
    schedule_data = ScheduleCreate(
        name="Test Schedule",
        week_type="A",
        shiftplans=[
            ShiftplanCreate(
                employee_id=1,
                date=date(2026, 5, 24),
                shift_id="morning",
                start_time=time(8, 0),
                end_time=time(16, 0),
                notes="Test shift",
            )
        ],
    )
    schedule = Schedule(
        name=schedule_data.name,
        week_type=schedule_data.week_type,
        status="draft",
    )
    db_session.add(schedule)
    db_session.flush()

    for sp_data in schedule_data.shiftplans:
        sp = Shiftplan(
            schedule_id=schedule.id,
            employee_id=sp_data.employee_id,
            date=sp_data.date,
            shift_id=sp_data.shift_id,
            start_time=sp_data.start_time,
            end_time=sp_data.end_time,
            notes=sp_data.notes,
        )
        db_session.add(sp)

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
    mock_response = {"job_id": 123}

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


@pytest.mark.asyncio
async def test_callback_endpoint_processes_results(client, db_session: Session, test_schedule: Schedule):
    """Test that callback endpoint correctly updates schedule."""
    test_schedule.status = "submitted"
    test_schedule.tito_job_id = 123
    db_session.add(test_schedule)
    db_session.commit()

    callback_payload = {
        "job_id": 123,
        "status": "SUCCESS",
        "metadata": {
            "status": "success",
            "solveTimeSeconds": 2.5,
            "timestamp": "2026-05-24T12:30:00",
        },
        "solution": {
            "assignments": [
                {
                    "employeeId": "emp_001",
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
            "employeeUtilization": {"emp_001": 0.95},
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
    assert len(shiftplans) > 0
    assert shiftplans[0].employee_id == 1  # parsed from "emp_001"
    assert shiftplans[0].shift_id == "morning"


@pytest.mark.asyncio
async def test_callback_endpoint_with_multiple_assignments(client, db_session: Session, test_schedule: Schedule):
    """Test callback with multiple employee assignments."""
    test_schedule.status = "submitted"
    test_schedule.tito_job_id = 124
    db_session.add(test_schedule)
    db_session.commit()

    callback_payload = {
        "job_id": 124,
        "status": "completed",
        "metadata": {
            "status": "success",
            "solveTimeSeconds": 3.2,
            "timestamp": "2026-05-24T12:35:00",
        },
        "solution": {
            "assignments": [
                {
                    "employeeId": "emp_001",
                    "date": "2026-05-24",
                    "shiftId": "morning",
                    "startTime": "08:00",
                    "endTime": "16:00",
                },
                {
                    "employeeId": "emp_002",
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
            "employeeUtilization": {"emp_001": 0.95, "emp_002": 0.88},
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
    assert {sp.employee_id for sp in shiftplans} == {1, 2}


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
