"""Integration tests for planer/employee team-scoped self-service endpoints."""


def test_get_my_teams_employee(client, employee_auth_headers, auth_headers, db_session):
    from app.db.models.employee import Employee
    from app.db.models.team import Team

    headers, emp_id = employee_auth_headers
    emp = db_session.query(Employee).filter(Employee.id == emp_id).first()
    team = Team(name="EmpTeam")
    db_session.add(team)
    db_session.commit()
    emp.teams.append(team)
    db_session.commit()

    response = client.get("/api/v1/my/teams", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "EmpTeam"


def test_get_my_team_schedule_employee(client, employee_auth_headers, auth_headers, db_session):
    from app.db.models.employee import Employee
    from app.db.models.team import Team

    headers, emp_id = employee_auth_headers
    emp = db_session.query(Employee).filter(Employee.id == emp_id).first()
    team = Team(name="EmpTeam2")
    db_session.add(team)
    db_session.commit()
    emp.teams.append(team)
    db_session.commit()

    # Create a colleague in the same team with a shift
    colleague = Employee(first_name="Col", last_name="League")
    db_session.add(colleague)
    db_session.commit()
    colleague.teams.append(team)
    db_session.commit()

    sched_resp = client.post(
        "/api/v1/schedules",
        json={
            "name": "TeamSchedule",
            "shiftplans": [
                {
                    "employee_id": colleague.id,
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

    response = client.get(f"/api/v1/my/team-schedule?schedule_id={schedule_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["employee_id"] == colleague.id


def test_get_my_team_schedule_outside_team_forbidden(client, employee_auth_headers, auth_headers, db_session):
    from app.db.models.employee import Employee

    headers, _ = employee_auth_headers

    foreign = Employee(first_name="Foreign", last_name="Colleague")
    db_session.add(foreign)
    db_session.commit()

    sched_resp = client.post(
        "/api/v1/schedules",
        json={
            "name": "ForeignSchedule",
            "shiftplans": [
                {
                    "employee_id": foreign.id,
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

    response = client.get(f"/api/v1/my/team-schedule?schedule_id={schedule_id}", headers=headers)
    assert response.status_code == 403


def test_get_my_teams_planer(client, planer_auth_headers):
    response = client.get("/api/v1/my/teams", headers=planer_auth_headers)
    assert response.status_code == 200
    # planer fixture assigns exactly one team
    assert len(response.json()) == 1


def test_get_my_team_schedule_requires_param(client, employee_auth_headers):
    headers, _ = employee_auth_headers
    response = client.get("/api/v1/my/team-schedule", headers=headers)
    assert response.status_code == 422
