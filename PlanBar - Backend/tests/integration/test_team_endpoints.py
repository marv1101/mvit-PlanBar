"""Tests for /api/v1/teams endpoints."""


def test_create_team_admin(client, auth_headers):
    response = client.post(
        "/api/v1/teams",
        json={"name": "Apotheke Nord", "color": "#aabbcc", "description": "Team Nord"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Apotheke Nord"
    assert data["color"] == "#aabbcc"
    assert data["description"] == "Team Nord"
    assert data["id"] > 0


def test_create_team_planer_forbidden(client, planer_auth_headers):
    # planer_auth_headers fixture defined below
    response = client.post(
        "/api/v1/teams",
        json={"name": "Foo"},
        headers=planer_auth_headers,
    )
    assert response.status_code == 403


def test_create_team_employee_forbidden(client, employee_auth_headers):
    headers, _ = employee_auth_headers
    response = client.post("/api/v1/teams", json={"name": "Foo"}, headers=headers)
    assert response.status_code == 403


def test_create_team_unauthenticated(client):
    response = client.post("/api/v1/teams", json={"name": "Foo"})
    assert response.status_code == 401


def test_create_duplicate_team(client, auth_headers):
    client.post("/api/v1/teams", json={"name": "Duplicate"}, headers=auth_headers)
    response = client.post("/api/v1/teams", json={"name": "Duplicate"}, headers=auth_headers)
    assert response.status_code == 409


def test_list_teams_admin(client, auth_headers):
    client.post("/api/v1/teams", json={"name": "Team A"}, headers=auth_headers)
    client.post("/api/v1/teams", json={"name": "Team B"}, headers=auth_headers)

    response = client.get("/api/v1/teams", headers=auth_headers)
    assert response.status_code == 200
    names = [t["name"] for t in response.json()["items"]]
    assert "Team A" in names
    assert "Team B" in names


def test_list_teams_planer(client, planer_auth_headers, auth_headers, planner_team):
    # planner_team fixture links planer to a team; planer sees only own teams via /mine
    client.post("/api/v1/teams", json={"name": "OtherTeam"}, headers=auth_headers)

    response = client.get("/api/v1/teams/mine", headers=planer_auth_headers)
    assert response.status_code == 200
    data = response.json()
    # planner sees only teams they belong to
    assert isinstance(data, list)
    assert all(t["id"] == planner_team for t in data)


def test_update_team_admin(client, auth_headers):
    team_id = client.post("/api/v1/teams", json={"name": "Upd"}, headers=auth_headers).json()["id"]
    response = client.put(
        f"/api/v1/teams/{team_id}",
        json={"name": "Renamed", "color": "#000000"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"
    assert response.json()["color"] == "#000000"


def test_update_team_planer_forbidden(client, planer_auth_headers, planner_team):
    response = client.put(
        f"/api/v1/teams/{planner_team}",
        json={"name": "Hacked"},
        headers=planer_auth_headers,
    )
    assert response.status_code == 403


def test_delete_team_admin(client, auth_headers):
    team_id = client.post("/api/v1/teams", json={"name": "ToDel"}, headers=auth_headers).json()["id"]
    response = client.delete(f"/api/v1/teams/{team_id}", headers=auth_headers)
    assert response.status_code == 204
    response = client.get(f"/api/v1/teams/{team_id}", headers=auth_headers)
    assert response.status_code == 404


def test_assign_employees_admin(client, auth_headers, db_session):
    from app.db.models.employee import Employee

    emp = Employee(first_name="X", last_name="Y")
    db_session.add(emp)
    db_session.commit()
    db_session.refresh(emp)

    team_id = client.post("/api/v1/teams", json={"name": "AssignT"}, headers=auth_headers).json()["id"]

    response = client.post(
        f"/api/v1/teams/{team_id}/employees",
        json={"employee_ids": [emp.id]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert emp.id in response.json()["employee_ids"]
