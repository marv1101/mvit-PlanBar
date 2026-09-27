"""Integration tests for the read-only kiosk board endpoint."""

from datetime import date, time, timedelta
from uuid import uuid4

import pytest
from app.services.kiosk_service import compute_kiosk_window


@pytest.fixture
def kiosk_auth_headers(client, db_session, auth_headers):
    """Auth headers for a 'kiosk' role user (display device, no employee link)."""
    from app.db.models.user import User

    suffix = uuid4().hex[:8]
    register_data = {
        "username": f"testkiosk-{suffix}",
        "email": f"kiosk-{suffix}@test.com",
        "password": "TestPass@123",
    }
    client.post("/api/v1/users", json=register_data)

    user = db_session.query(User).filter(User.email == register_data["email"]).first()
    user.role = "kiosk"
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/users/login",
        json={"email": register_data["email"], "password": register_data["password"]},
    )
    token = login_response.json()["access_token"]
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


def _in_window_dates():
    window_start, window_end = compute_kiosk_window()
    return window_start, window_end


def _make_employee(db_session, first_name, last_name, color=None):
    from app.db.models.employee import Employee

    emp = Employee(first_name=first_name, last_name=last_name, color=color)
    db_session.add(emp)
    db_session.commit()
    db_session.refresh(emp)
    return emp


def _make_team(db_session, name):
    from app.db.models.team import Team

    team = Team(name=name)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def _make_schedule(db_session, name, status="completed"):
    from app.db.models.schedule import Schedule

    schedule = Schedule(name=name, status=status)
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)
    return schedule


def _make_shiftplan(db_session, schedule, employee_id, d, start, end, **kwargs):
    from app.db.models.schedule import Shiftplan

    sp = Shiftplan(
        schedule_id=schedule.id,
        employee_id=employee_id,
        date=d,
        shift_id="frueh",
        start_time=start,
        end_time=end,
        week="A",
        **kwargs,
    )
    db_session.add(sp)
    db_session.commit()
    db_session.refresh(sp)
    return sp


def _unique(base):
    return f"{base}-{uuid4().hex[:8]}"


def test_kiosk_board_requires_auth(client):
    response = client.get("/api/v1/kiosk/board")
    assert response.status_code == 401


def test_kiosk_board_without_team_returns_all(
    client,
    db_session,
    kiosk_auth_headers,
):
    window_start, window_end = _in_window_dates()
    in_date = window_start + timedelta(days=1)
    out_date = window_end + timedelta(days=7)

    anna = _make_employee(db_session, "Anna", _unique("Kiosk"), color="#ef4444")
    bob = _make_employee(db_session, "Bob", _unique("Kiosk"))

    completed = _make_schedule(db_session, _unique("KioskCompletedBoard"))
    _make_shiftplan(db_session, completed, anna.id, in_date, time(6, 0), time(14, 0))
    _make_shiftplan(db_session, completed, bob.id, out_date, time(6, 0), time(14, 0))

    draft = _make_schedule(db_session, _unique("KioskDraftBoard"), status="draft")
    _make_shiftplan(db_session, draft, bob.id, in_date, time(6, 0), time(14, 0))

    response = client.get("/api/v1/kiosk/board", headers=kiosk_auth_headers)
    assert response.status_code == 200
    data = response.json()

    ws = date.fromisoformat(data["window_start"])
    we = date.fromisoformat(data["window_end"])
    assert ws.weekday() == 0  # Monday
    assert (we - ws).days == 13  # 14 consecutive days
    assert ws <= in_date <= we
    assert data["team"] is None

    employee_ids = {e["id"] for e in data["employees"]}
    assert {anna.id, bob.id}.issubset(employee_ids)

    shifts = data["shifts"]
    assert any(s["employee_id"] == anna.id and s["date"] == str(in_date) for s in shifts)
    # Bob's draft-schedule shift and out-of-window shift must NOT be returned.
    assert not any(s["employee_id"] == bob.id for s in shifts)

    assert "no-store" in response.headers.get("Cache-Control", "")


def test_kiosk_board_with_team_filters_employees_and_shifts(
    client,
    db_session,
    kiosk_auth_headers,
):
    window_start, _window_end = _in_window_dates()
    in_date = window_start + timedelta(days=2)

    team = _make_team(db_session, _unique("KioskTeam"))

    anna = _make_employee(db_session, "Anna", _unique("TeamKioskA"))
    anna.teams.append(team)
    bob = _make_employee(db_session, "Bob", _unique("TeamKioskB"))
    bob.teams.append(team)
    db_session.commit()
    db_session.refresh(anna)
    db_session.refresh(bob)

    carl = _make_employee(db_session, "Carl", _unique("TeamKioskC"))

    completed = _make_schedule(db_session, _unique("KioskTeamSched"))
    _make_shiftplan(db_session, completed, anna.id, in_date, time(8, 0), time(16, 0))
    _make_shiftplan(db_session, completed, carl.id, in_date, time(8, 0), time(16, 0))

    response = client.get(f"/api/v1/kiosk/board?team_id={team.id}", headers=kiosk_auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["team"] == {"id": team.id, "name": team.name}
    employee_ids = {e["id"] for e in data["employees"]}
    assert employee_ids == {anna.id, bob.id}

    shift_employee_ids = {s["employee_id"] for s in data["shifts"]}
    assert carl.id not in shift_employee_ids
    assert anna.id in shift_employee_ids


def test_kiosk_board_with_unknown_team_returns_404(client, kiosk_auth_headers):
    response = client.get("/api/v1/kiosk/board?team_id=999999", headers=kiosk_auth_headers)
    assert response.status_code == 404


def test_kiosk_board_planer_own_team_allowed(
    client,
    planer_auth_headers,
    planner_team,
    db_session,
):
    response = client.get(f"/api/v1/kiosk/board?team_id={planner_team}", headers=planer_auth_headers)
    assert response.status_code == 200


def test_kiosk_board_planer_foreign_team_forbidden(
    client,
    planer_auth_headers,
    db_session,
):
    foreign_team = _make_team(db_session, _unique("KioskForeignTeam"))
    response = client.get(f"/api/v1/kiosk/board?team_id={foreign_team.id}", headers=planer_auth_headers)
    assert response.status_code == 403


def test_kiosk_board_planer_without_team_scopes_to_own_teams(
    client,
    planer_auth_headers,
    planner_team,
    db_session,
):
    from app.db.models.team import Team

    window_start, _window_end = _in_window_dates()
    in_date = window_start + timedelta(days=3)

    planner_team_obj = db_session.query(Team).filter(Team.id == planner_team).first()

    gus = _make_employee(db_session, "Gus", _unique("PlanKioskGus"))
    gus.teams.append(planner_team_obj)
    db_session.commit()
    db_session.refresh(gus)

    other_team = _make_team(db_session, _unique("PlanKioskOther"))
    harold = _make_employee(db_session, "Harold", _unique("PlanKioskHarold"))
    harold.teams.append(other_team)
    db_session.commit()
    db_session.refresh(harold)

    completed = _make_schedule(db_session, _unique("PlanKioskSched"))
    _make_shiftplan(db_session, completed, gus.id, in_date, time(8, 0), time(16, 0))
    _make_shiftplan(db_session, completed, harold.id, in_date, time(8, 0), time(16, 0))

    response = client.get("/api/v1/kiosk/board", headers=planer_auth_headers)
    assert response.status_code == 200
    data = response.json()

    employee_ids = {e["id"] for e in data["employees"]}
    assert gus.id in employee_ids
    assert harold.id not in employee_ids

    shift_employee_ids = {s["employee_id"] for s in data["shifts"]}
    assert gus.id in shift_employee_ids
    assert harold.id not in shift_employee_ids


def test_kiosk_board_admin_with_team_allowed(
    client,
    auth_headers,
    db_session,
):
    team = _make_team(db_session, _unique("KioskAdminTeam"))
    response = client.get(f"/api/v1/kiosk/board?team_id={team.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["team"] == {"id": team.id, "name": team.name}


def test_kiosk_board_shift_fields_match_created_data(
    client,
    db_session,
    kiosk_auth_headers,
):
    window_start, _window_end = _in_window_dates()
    in_date = window_start + timedelta(days=3)

    last_name = _unique("FieldsKiosk")
    anna = _make_employee(db_session, "Anna", last_name)
    schedule = _make_schedule(db_session, _unique("KioskFieldsSched"))
    _make_shiftplan(
        db_session,
        schedule,
        anna.id,
        in_date,
        time(8, 0),
        time(16, 0),
        break_start="12:00",
        break_end="12:30",
        label="Frueh",
    )

    response = client.get("/api/v1/kiosk/board", headers=kiosk_auth_headers)
    assert response.status_code == 200
    data = response.json()

    matching = [s for s in data["shifts"] if s["employee_id"] == anna.id and s["date"] == str(in_date)]
    assert len(matching) == 1
    returned = matching[0]
    assert returned == {
        "employee_id": anna.id,
        "date": str(in_date),
        "start_time": "08:00:00",
        "end_time": "16:00:00",
        "break_start": "12:00",
        "break_end": "12:30",
        "label": "Frueh",
        "schedule_name": schedule.name,
    }

    employee_item = next(e for e in data["employees"] if e["id"] == anna.id)
    assert employee_item == {"id": anna.id, "name": f"Anna {last_name}", "color": None}


def test_admin_create_kiosk_user_without_password_change(client, auth_headers):
    """Admin can create a kiosk user with must_change_password=False via admin-create."""
    suffix = uuid4().hex[:8]
    response = client.post(
        "/api/v1/users/admin-create",
        json={
            "username": f"kiosk-tablet-{suffix}",
            "email": f"kiosk-tablet-{suffix}@test.com",
            "role": "kiosk",
            "must_change_password": False,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "kiosk"
    assert data["must_change_password"] is False
