"""Integration tests for auth + role-based scoping on /api/v1/sync endpoints.

Covered behavior:
- Unauthenticated requests are rejected (401) on all sync endpoints.
- ``GET /sync/initial`` and ``GET /sync/{resource_type}`` scope data by the
  caller's role (admin: all, planer: team scope, user: own records), mirroring
  the visibility of the regular REST endpoints.
- ETag / If-None-Match still work on the scoped payload.
- ``POST /sync/actions`` keeps its per-action role checks (status quo).
"""

from app.core.auth import create_access_token


def _create_role(db_session, name):
    from app.db.models.role import Role

    role = Role(name=name, color="#123456")
    db_session.add(role)
    db_session.commit()
    return role


def _create_employee(client, auth_headers, first="X", last="Y"):
    resp = client.post(
        "/api/v1/employees",
        json={"first_name": first, "last_name": last},
        headers=auth_headers,
    )
    return resp.json()["id"]


def _create_wish(client, auth_headers, employee_id, date="2026-06-01", note=None):
    resp = client.post(
        "/api/v1/requests",
        json={"employee_id": employee_id, "date": date, "type": "preferred", "note": note},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_schedule_with_shift(client, auth_headers, name, employee_id):
    resp = client.post(
        "/api/v1/schedules",
        json={
            "name": name,
            "shiftplans": [
                {
                    "employee_id": employee_id,
                    "date": "2026-07-01",
                    "shift_id": "frueh",
                    "start_time": "06:00:00",
                    "end_time": "14:00:00",
                }
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Authentication ────────────────────────────────────────────────────────────


def test_sync_initial_requires_auth(client):
    response = client.get("/api/v1/sync/initial")
    assert response.status_code == 401


def test_delta_sync_requires_auth(client):
    response = client.get("/api/v1/sync/employees")
    assert response.status_code == 401


def test_sync_actions_requires_auth(client):
    response = client.post("/api/v1/sync/actions", json={"actions": []})
    assert response.status_code == 401


def test_sync_rejects_invalid_token(client):
    response = client.get("/api/v1/sync/initial", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


def test_sync_rejects_unknown_user_token(client):
    token = create_access_token("999999")
    response = client.get("/api/v1/sync/initial", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


# ── Admin: full dataset ───────────────────────────────────────────────────────


def test_admin_sees_full_dataset(client, auth_headers, db_session):
    emp_a = _create_employee(client, auth_headers, "Admin", "SyncA")
    emp_b = _create_employee(client, auth_headers, "Admin", "SyncB")
    role = _create_role(db_session, "AdminSyncRole")
    _create_wish(client, auth_headers, emp_a, note="admin-sync")
    _create_wish(client, auth_headers, emp_b, note="admin-sync-foreign")
    _create_schedule_with_shift(client, auth_headers, "Admin Sync Schedule", emp_a)

    response = client.get("/api/v1/sync/initial", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    employee_ids = [e["id"] for e in data["employees"]]
    assert emp_a in employee_ids
    assert emp_b in employee_ids

    wish_employee_ids = [w["employee_id"] for w in data["requests"]]
    assert emp_a in wish_employee_ids
    assert emp_b in wish_employee_ids

    schedule_names = [s["name"] for s in data["schedules"]]
    assert "Admin Sync Schedule" in schedule_names

    shifts = data["shifts"]
    assert any(s["employee_id"] == emp_a for s in shifts)

    role_ids = [r["id"] for r in data["roles"]]
    assert role.id in role_ids  # roles are unscoped reference data


# ── User role: only own records ──────────────────────────────────────────────


def test_user_gets_only_own_employee(client, employee_auth_headers):
    headers, emp_id = employee_auth_headers

    response = client.get("/api/v1/sync/employees", headers=headers)
    assert response.status_code == 200
    employee_ids = [e["id"] for e in response.json()["data"]]
    assert employee_ids == [emp_id]


def test_user_initial_sync_scopes_employees_and_wishes(client, db_session, auth_headers, employee_auth_headers):
    headers, emp_id = employee_auth_headers
    foreign_emp = _create_employee(client, auth_headers, "Foreign", "SyncUser")
    own_wish = _create_wish(client, auth_headers, emp_id, note="own-wish")
    _create_wish(client, auth_headers, foreign_emp, note="foreign-wish")

    response = client.get("/api/v1/sync/initial", headers=headers)
    assert response.status_code == 200
    data = response.json()

    employee_ids = [e["id"] for e in data["employees"]]
    assert employee_ids == [emp_id]
    assert foreign_emp not in employee_ids

    wish_ids = [w["id"] for w in data["requests"]]
    assert own_wish["id"] in wish_ids
    assert all(w["employee_id"] == emp_id for w in data["requests"])


def test_user_without_teams_gets_no_schedules_or_shifts(client, employee_auth_headers):
    headers, _ = employee_auth_headers

    assert client.get("/api/v1/sync/schedules", headers=headers).json()["data"] == []
    assert client.get("/api/v1/sync/shifts", headers=headers).json()["data"] == []


def test_user_delta_sync_requests_only_own(client, db_session, auth_headers, employee_auth_headers):
    headers, emp_id = employee_auth_headers
    own_wish = _create_wish(client, auth_headers, emp_id, note="delta-own")

    response = client.get("/api/v1/sync/requests", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert any(w["id"] == own_wish["id"] for w in data)
    assert all(w["employee_id"] == emp_id for w in data)


def test_user_delta_sync_roles_are_unscoped_reference_data(client, db_session, employee_auth_headers):
    headers, _ = employee_auth_headers
    role = _create_role(db_session, "UserSyncRole")

    response = client.get("/api/v1/sync/roles", headers=headers)
    assert response.status_code == 200
    role_ids = [r["id"] for r in response.json()["data"]]
    assert role.id in role_ids


# ── Planer: team scope ───────────────────────────────────────────────────────


def test_planer_scoping(client, auth_headers, planner_team, planer_auth_headers, planer_employee_id):
    # Employee A joins the planner's team (assign_employees REPLACES the
    # roster, so the planer's own employee must be included), B stays outside.
    emp_a = _create_employee(client, auth_headers, "Team", "MemberA")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [planer_employee_id, emp_a]},
        headers=auth_headers,
    )
    emp_b = _create_employee(client, auth_headers, "Foreign", "MemberB")

    schedule_a = _create_schedule_with_shift(client, auth_headers, "Planer Team Sched", emp_a)
    schedule_b = _create_schedule_with_shift(client, auth_headers, "Planer Foreign Sched", emp_b)

    wish_a = _create_wish(client, auth_headers, emp_a, note="team-wish")
    _create_wish(client, auth_headers, emp_b, note="foreign-wish")

    # Employees: team members only (incl. the planer's own employee).
    response = client.get("/api/v1/sync/employees", headers=planer_auth_headers)
    assert response.status_code == 200
    employee_ids = [e["id"] for e in response.json()["data"]]
    assert emp_a in employee_ids
    assert planer_employee_id in employee_ids
    assert emp_b not in employee_ids

    # Schedules: only those referencing team members.
    response = client.get("/api/v1/sync/schedules", headers=planer_auth_headers)
    schedule_ids = [s["id"] for s in response.json()["data"]]
    assert schedule_a["id"] in schedule_ids
    assert schedule_b["id"] not in schedule_ids

    # Shifts: only shifts of visible schedules.
    response = client.get("/api/v1/sync/shifts", headers=planer_auth_headers)
    shifts = response.json()["data"]
    assert any(s["schedule_id"] == schedule_a["id"] and s["employee_id"] == emp_a for s in shifts)
    assert all(s["schedule_id"] != schedule_b["id"] for s in shifts)

    # Wishes: team members only.
    response = client.get("/api/v1/sync/requests", headers=planer_auth_headers)
    wish_ids = [w["id"] for w in response.json()["data"]]
    assert wish_a["id"] in wish_ids


def test_planer_initial_sync_excludes_foreign_data(
    client, auth_headers, planner_team, planer_auth_headers, planer_employee_id
):
    emp_a = _create_employee(client, auth_headers, "Team", "MemberInit")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [planer_employee_id, emp_a]},
        headers=auth_headers,
    )
    emp_b = _create_employee(client, auth_headers, "Foreign", "MemberInit")

    response = client.get("/api/v1/sync/initial", headers=planer_auth_headers)
    assert response.status_code == 200
    data = response.json()

    employee_ids = [e["id"] for e in data["employees"]]
    assert emp_a in employee_ids
    assert emp_b not in employee_ids


# ── ETag / conditional requests on scoped data ───────────────────────────────


def test_initial_sync_etag_304(client, auth_headers):
    first = client.get("/api/v1/sync/initial", headers=auth_headers)
    assert first.status_code == 200
    etag = first.headers.get("ETag")
    assert etag

    second = client.get("/api/v1/sync/initial", headers={**auth_headers, "If-None-Match": etag})
    assert second.status_code == 304


def test_delta_sync_etag_304(client, auth_headers):
    first = client.get("/api/v1/sync/employees", headers=auth_headers)
    assert first.status_code == 200
    etag = first.json()["etag"]

    second = client.get("/api/v1/sync/employees", headers={**auth_headers, "If-None-Match": etag})
    assert second.status_code == 304


def test_unknown_resource_type_returns_404(client, auth_headers):
    response = client.get("/api/v1/sync/unknown-resource", headers=auth_headers)
    assert response.status_code == 404


# ── /sync/actions: per-action role checks (status quo) ───────────────────────


def test_sync_actions_employee_can_create_own_wish(client, employee_auth_headers):
    headers, emp_id = employee_auth_headers

    response = client.post(
        "/api/v1/sync/actions",
        headers=headers,
        json={
            "actions": [
                {
                    "resource": "requests",
                    "action": "create",
                    "data": {"employee_id": emp_id, "date": "2026-06-01", "type": "preferred"},
                    "client_timestamp": "2026-06-01T00:00:00Z",
                }
            ]
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["success"] is True
    assert body["errors"] == []


def test_sync_actions_schedule_update_requires_admin(client, employee_auth_headers):
    headers, _ = employee_auth_headers

    response = client.post(
        "/api/v1/sync/actions",
        headers=headers,
        json={
            "actions": [
                {
                    "resource": "schedules",
                    "action": "update",
                    "data": {"id": 1, "name": "Hacked"},
                    "client_timestamp": "2026-06-01T00:00:00Z",
                }
            ]
        },
    )
    assert response.status_code == 403


def test_sync_actions_admin_can_update_schedule(client, auth_headers):
    schedule = _create_schedule(client, auth_headers, "Sync Action Sched")

    response = client.post(
        "/api/v1/sync/actions",
        headers=auth_headers,
        json={
            "actions": [
                {
                    "resource": "schedules",
                    "action": "update",
                    "data": {"id": schedule["id"], "name": "Renamed via Sync"},
                    "client_timestamp": "2026-06-01T00:00:00Z",
                }
            ]
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["success"] is True
    assert body["results"][0]["data"]["name"] == "Renamed via Sync"


def _create_schedule(client, auth_headers, name):
    resp = client.post("/api/v1/schedules", json={"name": name}, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── /sync/actions: ownership & team-scope checks ─────────────────────────────


def _action(resource, action, data):
    return {"resource": resource, "action": action, "data": data, "client_timestamp": "2026-06-01T00:00:00Z"}


def _post_actions(client, headers, actions):
    return client.post("/api/v1/sync/actions", headers=headers, json={"actions": actions})


def test_sync_actions_user_cannot_create_wish_for_foreign_employee(client, auth_headers, employee_auth_headers):
    headers, _emp_id = employee_auth_headers
    foreign = _create_employee(client, auth_headers, "Foreign", "SyncCreate")

    response = _post_actions(
        client, headers, [_action("requests", "create", {"employee_id": foreign, "date": "2026-06-01"})]
    )
    assert response.status_code == 403


def test_sync_actions_user_cannot_update_foreign_wish(client, auth_headers, employee_auth_headers):
    headers, _emp_id = employee_auth_headers
    foreign = _create_employee(client, auth_headers, "Foreign", "SyncUpdate")
    wish = _create_wish(client, auth_headers, foreign)

    response = _post_actions(client, headers, [_action("requests", "update", {"id": wish["id"], "note": "hijacked"})])
    assert response.status_code == 403


def test_sync_actions_user_can_update_own_wish_but_not_status(client, auth_headers, employee_auth_headers):
    headers, emp_id = employee_auth_headers
    wish = _create_wish(client, auth_headers, emp_id)

    update = _post_actions(client, headers, [_action("requests", "update", {"id": wish["id"], "note": "updated"})])
    assert update.status_code == 200
    assert update.json()["results"][0]["success"] is True

    status_change = _post_actions(
        client, headers, [_action("requests", "update", {"id": wish["id"], "status": "approved"})]
    )
    assert status_change.status_code == 403


def test_sync_actions_planer_can_review_team_wish(
    client, auth_headers, planner_team, planer_auth_headers, planer_employee_id
):
    emp_a = _create_employee(client, auth_headers, "Team", "WishReview")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [planer_employee_id, emp_a]},
        headers=auth_headers,
    )
    wish = _create_wish(client, auth_headers, emp_a)

    response = _post_actions(
        client, planer_auth_headers, [_action("requests", "update", {"id": wish["id"], "status": "approved"})]
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["data"]["status"] == "approved"


def test_sync_actions_planer_cannot_review_foreign_wish(
    client, auth_headers, planner_team, planer_auth_headers, planer_employee_id
):
    foreign = _create_employee(client, auth_headers, "Foreign", "WishReview")
    wish = _create_wish(client, auth_headers, foreign)

    response = _post_actions(
        client, planer_auth_headers, [_action("requests", "update", {"id": wish["id"], "status": "approved"})]
    )
    assert response.status_code == 403


def test_sync_actions_user_can_delete_own_wish(client, auth_headers, employee_auth_headers):
    headers, emp_id = employee_auth_headers
    wish = _create_wish(client, auth_headers, emp_id)

    response = _post_actions(client, headers, [_action("requests", "delete", {"id": wish["id"]})])
    assert response.status_code == 200
    assert response.json()["results"][0]["data"]["deleted"] is True


def test_sync_actions_user_cannot_delete_foreign_wish(client, auth_headers, employee_auth_headers):
    headers, _emp_id = employee_auth_headers
    foreign = _create_employee(client, auth_headers, "Foreign", "SyncDelete")
    wish = _create_wish(client, auth_headers, foreign)

    response = _post_actions(client, headers, [_action("requests", "delete", {"id": wish["id"]})])
    assert response.status_code == 403


def test_sync_actions_shift_update_denied_for_employee(client, auth_headers, employee_auth_headers):
    headers, emp_id = employee_auth_headers
    schedule = _create_schedule_with_shift(client, auth_headers, "Shift Deny Sched", emp_id)
    shift_id = schedule["shiftplans"][0]["id"]

    response = _post_actions(client, headers, [_action("shifts", "update", {"id": shift_id, "label": "Hacked"})])
    assert response.status_code == 403


def test_sync_actions_planer_can_update_team_shift(
    client, auth_headers, planner_team, planer_auth_headers, planer_employee_id
):
    emp_a = _create_employee(client, auth_headers, "Team", "ShiftEdit")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [planer_employee_id, emp_a]},
        headers=auth_headers,
    )
    schedule = _create_schedule_with_shift(client, auth_headers, "Planer Team Shift Sched", emp_a)
    shift_id = schedule["shiftplans"][0]["id"]

    response = _post_actions(
        client, planer_auth_headers, [_action("shifts", "update", {"id": shift_id, "label": "Planned"})]
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["data"]["label"] == "Planned"


def test_sync_actions_planer_cannot_update_foreign_shift(
    client, auth_headers, planner_team, planer_auth_headers, planer_employee_id
):
    foreign = _create_employee(client, auth_headers, "Foreign", "ShiftEdit")
    schedule = _create_schedule_with_shift(client, auth_headers, "Planer Foreign Shift Sched", foreign)
    shift_id = schedule["shiftplans"][0]["id"]

    response = _post_actions(
        client, planer_auth_headers, [_action("shifts", "update", {"id": shift_id, "label": "Hacked"})]
    )
    assert response.status_code == 403


def test_sync_actions_planer_cannot_reassign_shift_to_foreign_employee(
    client, auth_headers, planner_team, planer_auth_headers, planer_employee_id
):
    emp_a = _create_employee(client, auth_headers, "Team", "ShiftReassign")
    client.post(
        f"/api/v1/teams/{planner_team}/employees",
        json={"employee_ids": [planer_employee_id, emp_a]},
        headers=auth_headers,
    )
    foreign = _create_employee(client, auth_headers, "Foreign", "ShiftReassign")
    schedule = _create_schedule_with_shift(client, auth_headers, "Planer Reassign Sched", emp_a)
    shift_id = schedule["shiftplans"][0]["id"]

    response = _post_actions(
        client, planer_auth_headers, [_action("shifts", "update", {"id": shift_id, "employee_id": foreign})]
    )
    assert response.status_code == 403
