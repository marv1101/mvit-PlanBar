def test_approve_shift_wish(client, auth_headers):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Approve", "last_name": "Test"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    create_resp = client.post(
        "/api/v1/requests",
        json={
            "employee_id": emp_id,
            "date": "2026-06-01",
            "type": "preferred",
            "status": "pending",
        },
        headers=auth_headers,
    )
    wish_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "pending"

    resp = client.put(f"/api/v1/requests/{wish_id}/approve", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["reviewed_by"] is not None
    assert data["reviewed_at"] is not None


def test_reject_shift_wish(client, auth_headers):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Reject", "last_name": "Test"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    create_resp = client.post(
        "/api/v1/requests",
        json={
            "employee_id": emp_id,
            "date": "2026-06-02",
            "type": "unavailable",
            "status": "pending",
            "note": "Doctor appointment",
        },
        headers=auth_headers,
    )
    wish_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "pending"

    resp = client.put(
        f"/api/v1/requests/{wish_id}/reject",
        json={"rejection_reason": "Not enough staff"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["rejection_reason"] == "Not enough staff"
    assert data["reviewed_by"] is not None


def test_reject_shift_wish_without_reason(client, auth_headers):
    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "RejectNoReason", "last_name": "Test"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    create_resp = client.post(
        "/api/v1/requests",
        json={
            "employee_id": emp_id,
            "date": "2026-06-03",
            "type": "preferred",
            "status": "pending",
        },
        headers=auth_headers,
    )
    wish_id = create_resp.json()["id"]

    resp = client.put(f"/api/v1/requests/{wish_id}/reject", json={}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["rejection_reason"] is None


def test_get_pending_wishes_for_schedule(client, auth_headers, db_session):
    from app.db.models.shift_wish import ShiftWish

    db_session.query(ShiftWish).delete()
    db_session.commit()

    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Pending", "last_name": "List"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    # Create 3 wishes — all start as 'pending' (status field removed from create)
    wish_ids = []
    for day_offset in [1, 3, 5]:
        resp = client.post(
            "/api/v1/requests",
            json={
                "employee_id": emp_id,
                "date": f"2026-06-{day_offset:02d}",
                "type": "preferred",
            },
            headers=auth_headers,
        )
        wish_ids.append(resp.json()["id"])

    # Approve the third wish via the approve endpoint (admin only)
    client.put(f"/api/v1/requests/{wish_ids[2]}/approve", headers=auth_headers)

    schedule_resp = client.post(
        "/api/v1/schedules",
        json={
            "name": "Pending Wishes Schedule",
            "start_date": "2026-06-01",
            "end_date": "2026-06-07",
        },
        headers=auth_headers,
    )
    schedule_id = schedule_resp.json()["id"]

    resp = client.get(
        f"/api/v1/schedules/{schedule_id}/wishes/pending",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    for wish in data:
        assert wish["status"] == "pending"


def test_submit_blocked_by_pending_wishes(client, auth_headers, db_session):
    from app.db.models.shift_wish import ShiftWish

    db_session.query(ShiftWish).delete()
    db_session.commit()

    emp_resp = client.post(
        "/api/v1/employees",
        json={"first_name": "Block", "last_name": "Submit"},
        headers=auth_headers,
    )
    emp_id = emp_resp.json()["id"]

    schedule_resp = client.post(
        "/api/v1/schedules",
        json={
            "name": "Blocked Submit",
            "start_date": "2026-06-01",
            "end_date": "2026-06-07",
            "role_requirements": {"früh": "1"},
            "shiftplans": [
                {
                    "employee_id": emp_id,
                    "date": "2026-06-01",
                    "shift_id": "früh",
                    "start_time": "06:00",
                    "end_time": "14:00",
                },
            ],
        },
        headers=auth_headers,
    )
    schedule_id = schedule_resp.json()["id"]

    client.post(
        "/api/v1/requests",
        json={
            "employee_id": emp_id,
            "date": "2026-06-03",
            "type": "unavailable",
            "status": "pending",
        },
        headers=auth_headers,
    )

    resp = client.post(
        f"/api/v1/schedules/{schedule_id}/submit",
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert "pending" in resp.text.lower()
