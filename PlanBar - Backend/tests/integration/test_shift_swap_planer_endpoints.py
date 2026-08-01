"""Integration tests for planer RBAC on /api/v1/shift-swaps endpoints."""

from app.db.models.shift_swap import ShiftSwapRequest


def _create_employee(client, auth_headers, first, last):
    return client.post(
        "/api/v1/employees",
        json={"first_name": first, "last_name": last},
        headers=auth_headers,
    ).json()["id"]


def _create_shift_for_employee(client, auth_headers, emp_id):
    sched_resp = client.post(
        "/api/v1/schedules",
        json={
            "name": "SwapSched",
            "shiftplans": [
                {
                    "employee_id": emp_id,
                    "date": "2026-07-01",
                    "shift_id": "frueh",
                    "start_time": "06:00:00",
                    "end_time": "14:00:00",
                }
            ],
        },
        headers=auth_headers,
    )
    schedule_id = sched_resp.json()["id"]
    shifts = client.get(
        f"/api/v1/schedules/{schedule_id}/shifts", headers=auth_headers
    ).json()["items"]
    return shifts[0]["id"]


def test_planer_cannot_approve_swap_with_foreign_employee(
    client, auth_headers, planer_auth_headers, planner_team, db_session, planer_employee_id
):
    emp1 = _create_employee(client, auth_headers, "Own", "Swap")
    foreign = _create_employee(client, auth_headers, "Foreign", "Swap")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [planer_employee_id, emp1]},
        headers=auth_headers,
    )

    shift1 = _create_shift_for_employee(client, auth_headers, emp1)
    shift2 = _create_shift_for_employee(client, auth_headers, foreign)

    swap = ShiftSwapRequest(
        employee_id=emp1,
        requester_shift_id=shift1,
        target_employee_id=foreign,
        target_shift_id=shift2,
        status="pending",
    )
    db_session.add(swap)
    db_session.commit()
    db_session.refresh(swap)

    response = client.put(
        f"/api/v1/shift-swaps/{swap.id}/approve", headers=planer_auth_headers
    )
    assert response.status_code == 403


def test_planer_can_approve_swap_with_team_members(
    client, auth_headers, planer_auth_headers, planner_team, db_session, planer_employee_id
):
    emp1 = _create_employee(client, auth_headers, "Own1", "Swap")
    emp2 = _create_employee(client, auth_headers, "Own2", "Swap")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [planer_employee_id, emp1, emp2]},
        headers=auth_headers,
    )

    shift1 = _create_shift_for_employee(client, auth_headers, emp1)
    shift2 = _create_shift_for_employee(client, auth_headers, emp2)

    swap = ShiftSwapRequest(
        employee_id=emp1,
        requester_shift_id=shift1,
        target_employee_id=emp2,
        target_shift_id=shift2,
        status="pending",
    )
    db_session.add(swap)
    db_session.commit()
    db_session.refresh(swap)

    response = client.put(
        f"/api/v1/shift-swaps/{swap.id}/approve", headers=planer_auth_headers
    )
    assert response.status_code == 200


def test_employee_cannot_approve_swap(client, employee_auth_headers):
    headers, _ = employee_auth_headers
    response = client.put("/api/v1/shift-swaps/1/approve", headers=headers)
    assert response.status_code == 403