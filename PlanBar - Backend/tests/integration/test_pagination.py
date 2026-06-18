"""Tests for offset/limit pagination on list endpoints."""

import uuid


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique(suffix: str) -> str:
    """Generate a short unique string to avoid collisions across tests."""
    return f"{suffix}_{uuid.uuid4().hex[:6]}"


def _create_users(client, n: int, auth_headers) -> list[dict]:
    """Register *n* distinct users via the public API and return their data."""
    created = []
    for i in range(n):
        tag = _unique(f"u{i}")
        resp = client.post(
            "/api/v1/users",
            json={
                "username": tag,
                "email": f"{tag}@example.com",
                "password": "TestPass@123",
            },
        )
        assert resp.status_code == 201, resp.text
        created.append(resp.json())
    return created


def _create_employees(client, n: int, auth_headers) -> list[dict]:
    created = []
    for i in range(n):
        tag = _unique(f"e{i}")
        resp = client.post(
            "/api/v1/employees",
            json={"first_name": tag, "last_name": "Pagination"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        created.append(resp.json())
    return created


def _create_schedules(client, n: int, auth_headers) -> list[dict]:
    created = []
    for i in range(n):
        resp = client.post(
            "/api/v1/schedules",
            json={"name": _unique(f"sch{i}")},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        created.append(resp.json())
    return created


def _create_shift_wishes(client, n: int, auth_headers) -> list[dict]:
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": _unique("wh"), "last_name": "PagTest"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]
    created = []
    for i in range(n):
        resp = client.post(
            "/api/v1/requests",
            json={
                "employee_id": emp_id,
                "date": f"2026-07-{i + 1:02d}",
                "type": "preferred",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        created.append(resp.json())
    return created


# ---------------------------------------------------------------------------
# User list pagination
# ---------------------------------------------------------------------------

def test_users_pagination(client, auth_headers):
    _create_users(client, 10, auth_headers)
    resp = client.get("/api/v1/users", headers=auth_headers, params={"limit": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 3
    assert body["total"] >= 10 + 1  # +1 for the admin created by auth_headers
    assert body["offset"] == 0
    assert body["limit"] == 3


def test_users_pagination_offset(client, auth_headers):
    _create_users(client, 5, auth_headers)
    resp = client.get(
        "/api/v1/users",
        headers=auth_headers,
        params={"offset": 2, "limit": 2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["offset"] == 2


# ---------------------------------------------------------------------------
# Employee list pagination
# ---------------------------------------------------------------------------

def test_employees_pagination(client, auth_headers):
    _create_employees(client, 10, auth_headers)
    resp = client.get("/api/v1/employees", headers=auth_headers, params={"limit": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 3
    assert body["total"] >= 10
    assert body["limit"] == 3


# ---------------------------------------------------------------------------
# Schedule list pagination
# ---------------------------------------------------------------------------

def test_schedules_pagination(client, auth_headers):
    _create_schedules(client, 10, auth_headers)
    resp = client.get("/api/v1/schedules", headers=auth_headers, params={"limit": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 3
    assert body["total"] >= 10
    assert body["limit"] == 3


# ---------------------------------------------------------------------------
# Shift wish (requests) pagination
# ---------------------------------------------------------------------------

def test_shift_wishes_pagination(client, auth_headers):
    _create_shift_wishes(client, 10, auth_headers)
    resp = client.get("/api/v1/requests", headers=auth_headers, params={"limit": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 3
    assert body["total"] >= 10
    assert body["limit"] == 3


# ---------------------------------------------------------------------------
# Defaults & caps
# ---------------------------------------------------------------------------

def test_pagination_defaults(client, auth_headers):
    """Without explicit params, offset=0 and limit=50."""
    resp = client.get("/api/v1/users", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["offset"] == 0
    assert body["limit"] == 50


def test_pagination_max_limit(client, auth_headers):
    """limit > 200 is rejected by validation."""
    resp = client.get("/api/v1/users", headers=auth_headers, params={"limit": 201})
    assert resp.status_code == 422  # FastAPI validation error


def test_shift_wishes_pagination_page2(client, auth_headers):
    """Fetch second page and verify different items returned."""
    _create_shift_wishes(client, 5, auth_headers)
    page1 = client.get(
        "/api/v1/requests", headers=auth_headers, params={"limit": 2, "offset": 0}
    ).json()
    page2 = client.get(
        "/api/v1/requests", headers=auth_headers, params={"limit": 2, "offset": 2}
    ).json()
    assert page1["items"][0]["id"] != page2["items"][0]["id"]
    assert page2["offset"] == 2
