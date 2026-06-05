from datetime import date, time

from app.db.models.employee import Contract, Timecard
from app.db.models.schedule import Schedule, Shiftplan


def test_get_time_account_empty(client, auth_headers):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Empty", "last_name": "Account"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    resp = client.get(f"/api/v1/employees/{emp_id}/time-account", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["employee_id"] == emp_id
    assert data["current_balance"] == 0.0
    assert data["history"] == []
    assert data["projected"] is None


def test_get_time_account_with_history(client, auth_headers, db_session):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "History", "last_name": "Test"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    tc1 = Timecard(employee_id=emp_id, week=22, year=2026, scheduled_hours=38.0, contract_hours=40.0, balance=-2.0)
    tc2 = Timecard(employee_id=emp_id, week=23, year=2026, scheduled_hours=42.0, contract_hours=40.0, balance=0.0)
    db_session.add_all([tc1, tc2])
    db_session.commit()

    resp = client.get(f"/api/v1/employees/{emp_id}/time-account", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_balance"] == 0.0
    assert len(data["history"]) == 2
    assert data["history"][0] == dict(week=22, year=2026, scheduled_hours=38.0, contract_hours=40.0, delta=-2.0, balance=-2.0)
    assert data["history"][1] == dict(week=23, year=2026, scheduled_hours=42.0, contract_hours=40.0, delta=2.0, balance=0.0)


def test_get_time_account_with_projected(client, auth_headers, db_session):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Projected", "last_name": "Test"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    contract = Contract(employee_id=emp_id, weekly_working_hours=35.0, break_time=30)
    db_session.add(contract)
    db_session.commit()

    tc = Timecard(employee_id=emp_id, week=22, year=2026, scheduled_hours=35.0, contract_hours=35.0, balance=5.0)
    db_session.add(tc)
    db_session.commit()

    schedule = Schedule(
        name="Current",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="completed",
    )
    db_session.add(schedule)
    db_session.commit()

    sp = Shiftplan(
        schedule_id=schedule.id, employee_id=emp_id, date=date(2026, 6, 1),
        shift_id="früh", start_time=time(6, 0), end_time=time(14, 0),
    )
    db_session.add(sp)
    db_session.commit()

    resp = client.get(f"/api/v1/employees/{emp_id}/time-account", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_balance"] == 5.0
    assert data["projected"] is not None
    assert data["projected"]["from_schedule"] == 7.5
    assert data["projected"]["expected_balance_after"] == 5.0 + 7.5 - 35.0


def test_get_time_account_not_found(client, auth_headers):
    resp = client.get("/api/v1/employees/99999/time-account", headers=auth_headers)
    assert resp.status_code == 404
