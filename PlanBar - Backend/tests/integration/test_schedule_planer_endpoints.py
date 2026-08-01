"""Integration tests for planer RBAC on /api/v1/schedules endpoints.

These tests confirm that a *planer* role user can interact with schedules
that include their team members, but is rejected (403) when touching
schedules that reference foreign employees.
"""



def _create_employee(client, auth_headers, db_session, first="X", last="Y"):
    resp = client.post(
        "/api/v1/employees",
        json={"first_name": first, "last_name": last},
        headers=auth_headers,
    )
    return resp.json()["id"]


def _link_to_team_and_user(db_session, employee_id, team_id, role="planer"):
    from app.core.auth import generate_password, hash_password
    from app.db.models.employee import Employee
    from app.db.models.team import Team
    from app.db.models.user import User

    emp = db_session.query(Employee).filter(Employee.id == employee_id).first()
    if team_id:
        team = db_session.query(Team).filter(Team.id == team_id).first()
        emp.teams.append(team)

    username = f"sched_planer_{employee_id}"
    email = f"{username}@example.com"
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(generate_password()),
        role=role,
        employee_id=employee_id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user, email


def _login(client, email):
    # We can't recover the password but we can issue a fresh password-update directly.
    # Simpler: just use the seeded flow + auth_headers for admin; for planer we rely
    # on the planer_auth_headers fixture.
    raise NotImplementedError("Use planer_auth_headers fixture instead.")


def test_planer_can_create_schedule_own_team(client, auth_headers, db_session, planner_team, planer_auth_headers, planer_employee_id):
    emp_id = _create_employee(client, auth_headers, db_session, "Own", "Plan")
    # Link this employee to the planner_team via API endpoint
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [planer_employee_id, emp_id]},
        headers=auth_headers,
    )

    # Make planer user also a member of planner_team (already done by fixture)
    # Now planner creates a schedule with shift for emp_id (same team)
    response = client.post(
        "/api/v1/schedules",
        json={
            "name": "PlanerSched",
            "week_type": "A",
            "shiftplans": [
                {
                    "employee_id": emp_id,
                    "date": "2026-07-01",
                    "shift_id": "frueh",
                    "start_time": "06:00:00",
                    "end_time": "14:00:00",
                    "week": "A",
                }
            ],
        },
        headers=planer_auth_headers,
    )
    assert response.status_code == 201, response.text


def test_planer_cannot_create_schedule_for_foreign_employee(client, auth_headers, db_session, planer_auth_headers):
    foreign_emp_id = _create_employee(client, auth_headers, db_session, "Foreign", "Emp")

    response = client.post(
        "/api/v1/schedules",
        json={
            "name": "ForeignSched",
            "week_type": "A",
            "shiftplans": [
                {
                    "employee_id": foreign_emp_id,
                    "date": "2026-07-01",
                    "shift_id": "frueh",
                    "start_time": "06:00:00",
                    "end_time": "14:00:00",
                    "week": "A",
                }
            ],
        },
        headers=planer_auth_headers,
    )
    assert response.status_code == 403


def test_employee_cannot_create_schedule(client, employee_auth_headers):
    headers, _ = employee_auth_headers
    response = client.post(
        "/api/v1/schedules",
        json={"name": "TrySched"},
        headers=headers,
    )
    assert response.status_code == 403


def test_planer_can_update_own_schedule(client, auth_headers, db_session, planner_team, planer_auth_headers, planer_employee_id):
    emp_id = _create_employee(client, auth_headers, db_session, "Upd", "Emp")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [planer_employee_id, emp_id]},
        headers=auth_headers,
    )

    create_resp = client.post(
        "/api/v1/schedules",
        json={
            "name": "OwnSched",
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
        headers=planer_auth_headers,
    )
    schedule_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/schedules/{schedule_id}",
        json={"name": "Renamed by Planer"},
        headers=planer_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed by Planer"


def test_planer_cannot_update_foreign_schedule(client, auth_headers, db_session, planer_auth_headers):
    foreign_emp_id = _create_employee(client, auth_headers, db_session, "Foreign2", "Emp")
    create_resp = client.post(
        "/api/v1/schedules",
        json={
            "name": "AdminForeignSched",
            "shiftplans": [
                {
                    "employee_id": foreign_emp_id,
                    "date": "2026-07-01",
                    "shift_id": "frueh",
                    "start_time": "06:00:00",
                    "end_time": "14:00:00",
                }
            ],
        },
        headers=auth_headers,
    )
    schedule_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/schedules/{schedule_id}",
        json={"name": "Hacked"},
        headers=planer_auth_headers,
    )
    assert response.status_code == 403


def test_planer_can_list_only_own_team_schedules(client, auth_headers, db_session, planner_team, planer_auth_headers, planer_employee_id):
    own_emp_id = _create_employee(client, auth_headers, db_session, "ListOwn", "Emp")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [planer_employee_id, own_emp_id]},
        headers=auth_headers,
    )
    foreign_emp_id = _create_employee(client, auth_headers, db_session, "ListForeign", "Emp")

    # Own-team schedule (via admin)
    client.post(
        "/api/v1/schedules",
        json={
            "name": "VisibleToPlaner",
            "shiftplans": [
                {
                    "employee_id": own_emp_id,
                    "date": "2026-07-01",
                    "shift_id": "frueh",
                    "start_time": "06:00:00",
                    "end_time": "14:00:00",
                }
            ],
        },
        headers=auth_headers,
    )
    # Foreign schedule
    client.post(
        "/api/v1/schedules",
        json={
            "name": "HiddenFromPlaner",
            "shiftplans": [
                {
                    "employee_id": foreign_emp_id,
                    "date": "2026-07-01",
                    "shift_id": "frueh",
                    "start_time": "06:00:00",
                    "end_time": "14:00:00",
                }
            ],
        },
        headers=auth_headers,
    )

    response = client.get("/api/v1/schedules", headers=planer_auth_headers)
    assert response.status_code == 200
    names = [s["name"] for s in response.json()["items"]]
    assert "VisibleToPlaner" in names
    assert "HiddenFromPlaner" not in names


def test_planer_can_delete_own_schedule(client, auth_headers, db_session, planner_team, planer_auth_headers, planer_employee_id):
    emp_id = _create_employee(client, auth_headers, db_session, "Del", "Emp")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [planer_employee_id, emp_id]},
        headers=auth_headers,
    )
    create_resp = client.post(
        "/api/v1/schedules",
        json={
            "name": "DelSched",
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
        headers=planer_auth_headers,
    )
    schedule_id = create_resp.json()["id"]

    response = client.delete(f"/api/v1/schedules/{schedule_id}", headers=planer_auth_headers)
    assert response.status_code == 204


def test_planer_cannot_replace_foreign_shifts(client, auth_headers, db_session, planer_auth_headers):
    foreign_emp_id = _create_employee(client, auth_headers, db_session, "ReplaceForeign", "Emp")
    create_resp = client.post(
        "/api/v1/schedules",
        json={
            "name": "ReplaceSched",
            "shiftplans": [
                {
                    "employee_id": foreign_emp_id,
                    "date": "2026-07-01",
                    "shift_id": "frueh",
                    "start_time": "06:00:00",
                    "end_time": "14:00:00",
                }
            ],
        },
        headers=auth_headers,
    )
    schedule_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/schedules/{schedule_id}/shifts",
        json={
            "shiftplans": [
                {
                    "employee_id": foreign_emp_id,
                    "date": "2026-07-01",
                    "shift_id": "frueh",
                    "start_time": "06:00:00",
                    "end_time": "14:00:00",
                }
            ]
        },
        headers=planer_auth_headers,
    )
    assert response.status_code == 403


def test_planer_cannot_view_pending_wishes_foreign(client, auth_headers, db_session, planer_auth_headers):
    foreign_emp_id = _create_employee(client, auth_headers, db_session, "ForeignWish", "Emp")
    create_resp = client.post(
        "/api/v1/schedules",
        json={
            "name": "WishesSched",
            "start_date": "2026-07-01",
            "end_date": "2026-07-07",
            "shiftplans": [
                {
                    "employee_id": foreign_emp_id,
                    "date": "2026-07-01",
                    "shift_id": "frueh",
                    "start_time": "06:00:00",
                    "end_time": "14:00:00",
                }
            ],
        },
        headers=auth_headers,
    )
    schedule_id = create_resp.json()["id"]

    response = client.get(
        f"/api/v1/schedules/{schedule_id}/wishes/pending",
        headers=planer_auth_headers,
    )
    assert response.status_code == 403