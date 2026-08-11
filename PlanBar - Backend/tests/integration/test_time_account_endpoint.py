from datetime import date, time

import pytest
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


def _entry(
    week,
    year,
    scheduled_hours,
    contract_hours,
    delta,
    balance,
    manual_adjustment=0.0,
    adjustment_reason=None,
    total_change=None,
):
    if total_change is None:
        total_change = delta + manual_adjustment
    return {
        "week": week,
        "year": year,
        "scheduled_hours": scheduled_hours,
        "contract_hours": contract_hours,
        "delta": delta,
        "balance": balance,
        "manual_adjustment": manual_adjustment,
        "adjustment_reason": adjustment_reason,
        "total_change": total_change,
    }


def test_get_time_account_with_history(client, auth_headers, db_session):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "History", "last_name": "Test"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    tc1 = Timecard(
        employee_id=emp_id,
        week=22,
        year=2026,
        scheduled_hours=38.0,
        contract_hours=40.0,
        balance=-2.0,
    )
    tc2 = Timecard(
        employee_id=emp_id,
        week=23,
        year=2026,
        scheduled_hours=42.0,
        contract_hours=40.0,
        balance=0.0,
    )
    db_session.add_all([tc1, tc2])
    db_session.commit()

    resp = client.get(f"/api/v1/employees/{emp_id}/time-account", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_balance"] == 0.0
    assert len(data["history"]) == 2
    assert data["history"][0] == _entry(22, 2026, 38.0, 40.0, -2.0, -2.0)
    assert data["history"][1] == _entry(23, 2026, 42.0, 40.0, 2.0, 0.0)


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

    tc = Timecard(
        employee_id=emp_id,
        week=22,
        year=2026,
        scheduled_hours=35.0,
        contract_hours=35.0,
        balance=5.0,
    )
    db_session.add(tc)
    db_session.commit()

    schedule = Schedule(
        name="Current",
        start_date=date(2099, 12, 25),
        end_date=date(2099, 12, 31),
        status="submitted",
    )
    db_session.add(schedule)
    db_session.commit()

    sp = Shiftplan(
        schedule_id=schedule.id,
        employee_id=emp_id,
        date=date(2099, 12, 25),
        shift_id="früh",
        start_time=time(6, 0),
        end_time=time(14, 0),
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


def test_get_time_account_projected_multiweek(client, auth_headers, db_session):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Multiweek", "last_name": "Proj"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    contract = Contract(employee_id=emp_id, weekly_working_hours=40.0, break_time=30)
    db_session.add(contract)
    db_session.commit()

    tc = Timecard(
        employee_id=emp_id,
        week=21,
        year=2026,
        scheduled_hours=40.0,
        contract_hours=40.0,
        balance=0.0,
    )
    db_session.add(tc)
    db_session.commit()

    schedule = Schedule(
        name="Multiweek Submitted",
        start_date=date(2100, 1, 1),
        end_date=date(2100, 1, 28),
        status="submitted",
    )
    db_session.add(schedule)
    db_session.commit()

    sp1 = Shiftplan(
        schedule_id=schedule.id,
        employee_id=emp_id,
        date=date(2100, 1, 1),
        shift_id="früh",
        start_time=time(6, 0),
        end_time=time(14, 0),
    )
    sp2 = Shiftplan(
        schedule_id=schedule.id,
        employee_id=emp_id,
        date=date(2100, 1, 8),
        shift_id="früh",
        start_time=time(6, 0),
        end_time=time(14, 0),
    )
    db_session.add_all([sp1, sp2])
    db_session.commit()

    resp = client.get(f"/api/v1/employees/{emp_id}/time-account", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["projected"] is not None

    from_schedule = data["projected"]["from_schedule"]
    expected_balance = data["projected"]["expected_balance_after"]

    effective_per_shift = 7.5
    assert from_schedule == pytest.approx(2 * effective_per_shift)

    contract_weekly = 40.0
    assert expected_balance == pytest.approx(0.0 + from_schedule - 2 * contract_weekly)


def test_get_all_time_accounts_batch(client, auth_headers, db_session):
    emp1_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Batch", "last_name": "One"},
        headers=auth_headers,
    )
    emp1_id = emp1_resp.json()["id"]
    emp2_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Batch", "last_name": "Two"},
        headers=auth_headers,
    )
    emp2_id = emp2_resp.json()["id"]

    tc1 = Timecard(
        employee_id=emp1_id,
        week=22,
        year=2026,
        scheduled_hours=38.0,
        contract_hours=40.0,
        balance=-2.0,
    )
    tc2 = Timecard(
        employee_id=emp2_id,
        week=22,
        year=2026,
        scheduled_hours=42.0,
        contract_hours=40.0,
        balance=2.0,
    )
    db_session.add_all([tc1, tc2])
    db_session.commit()

    resp = client.get("/api/v1/employees/time-accounts?limit=200", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    items = data["items"]
    assert len(items) >= 2

    emp1_data = next(e for e in items if e["employee_id"] == emp1_id)
    assert emp1_data["current_balance"] == -2.0
    assert len(emp1_data["history"]) == 1
    assert emp1_data["history"][0] == _entry(22, 2026, 38.0, 40.0, -2.0, -2.0)

    emp2_data = next(e for e in items if e["employee_id"] == emp2_id)
    assert emp2_data["current_balance"] == 2.0
    assert len(emp2_data["history"]) == 1


def test_get_all_time_accounts_requires_admin(client):
    resp = client.get("/api/v1/employees/time-accounts")
    assert resp.status_code == 401


def test_adjust_time_account_add_hours(client, auth_headers, db_session):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Adjust", "last_name": "Test"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    tc = Timecard(
        employee_id=emp_id,
        week=22,
        year=2026,
        scheduled_hours=38.0,
        contract_hours=40.0,
        balance=-2.0,
    )
    db_session.add(tc)
    db_session.commit()

    resp = client.post(
        f"/api/v1/employees/{emp_id}/time-account/adjust",
        json={"delta_hours": 5.0, "reason": "Korrektur Überstunden"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_balance"] == 3.0
    assert len(data["history"]) == 1
    entry = data["history"][0]
    assert entry["delta"] == -2.0
    assert entry["scheduled_hours"] == 38.0
    assert entry["contract_hours"] == 40.0
    assert entry["manual_adjustment"] == 5.0
    assert entry["adjustment_reason"] == "Korrektur Überstunden"
    assert entry["balance"] == 3.0
    assert entry["total_change"] == 3.0


def test_adjust_time_account_cumulative_reason(client, auth_headers, db_session):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Cumul", "last_name": "Reason"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    tc = Timecard(
        employee_id=emp_id,
        week=22,
        year=2026,
        scheduled_hours=40.0,
        contract_hours=40.0,
        balance=0.0,
    )
    db_session.add(tc)
    db_session.commit()

    resp1 = client.post(
        f"/api/v1/employees/{emp_id}/time-account/adjust",
        json={"delta_hours": 3.0, "reason": "Überstunden Juni"},
        headers=auth_headers,
    )
    assert resp1.status_code == 200

    resp2 = client.post(
        f"/api/v1/employees/{emp_id}/time-account/adjust",
        json={"delta_hours": 2.0, "reason": "Korrektur Juli"},
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["current_balance"] == 5.0
    entry = data["history"][0]
    assert entry["manual_adjustment"] == 5.0
    assert entry["adjustment_reason"] == "Überstunden Juni; Korrektur Juli"


def test_adjust_time_account_subtract_hours(client, auth_headers, db_session):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Adjust", "last_name": "Sub"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    tc = Timecard(
        employee_id=emp_id,
        week=22,
        year=2026,
        scheduled_hours=42.0,
        contract_hours=40.0,
        balance=2.0,
    )
    db_session.add(tc)
    db_session.commit()

    resp = client.post(
        f"/api/v1/employees/{emp_id}/time-account/adjust",
        json={"delta_hours": -5.0},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_balance"] == -3.0


def test_adjust_time_account_requires_admin(client, auth_headers, db_session):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "No", "last_name": "Access"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    client.cookies.clear()

    resp = client.post(
        f"/api/v1/employees/{emp_id}/time-account/adjust",
        json={"delta_hours": 1.0},
    )
    assert resp.status_code == 401


def test_adjust_time_account_no_existing_timecard(client, auth_headers, db_session):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Fresh", "last_name": "Start"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    resp = client.post(
        f"/api/v1/employees/{emp_id}/time-account/adjust",
        json={"delta_hours": 10.0, "reason": "Startguthaben"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_balance"] == 10.0
    assert len(data["history"]) == 1
    assert data["history"][0]["manual_adjustment"] == 10.0
    assert data["history"][0]["balance"] == 10.0


def test_adjust_time_account_with_callback_timecard(client, auth_headers, db_session):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Callback", "last_name": "Conflict"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    contract = Contract(employee_id=emp_id, weekly_working_hours=40.0, break_time=30)
    db_session.add(contract)
    db_session.commit()

    schedule = Schedule(
        name="Current",
        start_date=date(2026, 6, 15),
        end_date=date(2026, 6, 21),
        status="completed",
    )
    db_session.add(schedule)
    db_session.commit()

    sp = Shiftplan(
        schedule_id=schedule.id,
        employee_id=emp_id,
        date=date(2026, 6, 15),
        shift_id="früh",
        start_time=time(6, 0),
        end_time=time(14, 0),
    )
    db_session.add(sp)
    db_session.commit()

    from app.services.tito_callback import update_timecards_from_schedule

    update_timecards_from_schedule(db_session, schedule)

    resp = client.post(
        f"/api/v1/employees/{emp_id}/time-account/adjust",
        json={"delta_hours": 5.0, "reason": "Korrektur"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    db_session.expire_all()
    tc_after = db_session.query(Timecard).filter(Timecard.employee_id == emp_id).first()
    assert data["current_balance"] == tc_after.balance


def test_adjust_time_account_not_found(client, auth_headers):
    resp = client.post(
        "/api/v1/employees/99999/time-account/adjust",
        json={"delta_hours": 1.0},
        headers=auth_headers,
    )
    assert resp.status_code == 404
