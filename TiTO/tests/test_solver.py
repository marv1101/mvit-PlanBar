from tito.solver import build_model, solve_model


def test_solver_generates_assignments_for_valid_payload():
    payload = {
        "metadata": {"jobId": "job-001"},
        "shiftTemplates": [{"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}}],
        "employees": [{"id": "emp_001", "skills": ["Apotheker"], "forbiddenDates": []}],
        "wishes": [{"employeeId": "emp_001", "type": "PREFER_SHIFT", "shiftId": "S_FRUEH", "date": "2026-01-02"}],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)

    assert result["metadata"]["status"] == "SUCCESS"
    assert len(result["solution"]["assignments"]) == 1
    assert result["metrics"]["wishFulfillmentRate"] == 100.0
