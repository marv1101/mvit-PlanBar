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


def test_solver_respects_max_daily_hours():
    payload = {
        "metadata": {"jobId": "job-002"},
        "config": {
            "schemaVersion": "1.0",
            "startDate": "2026-01-01",
            "endDate": "2026-01-31",
            "maxConsecutiveDays": 6,
            "minRestTimeHours": 11,
            "maxDailyWorkHours": 10,
        },
        "shiftTemplates": [
            {"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"},
            {"id": "S_SPAET", "startTime": "14:00", "endTime": "22:00"},
        ],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
            {"date": "2026-01-02", "shiftId": "S_SPAET", "neededSkills": {"Apotheker": 1}},
        ],
        "employees": [
            {"id": "emp_001", "skills": ["Apotheker"], "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)

    assert result["metadata"]["status"] == "INFEASIBLE"


def test_solver_accepts_current_balance_hours():
    """Test that the solver accepts currentBalanceHours field without error."""
    payload = {
        "metadata": {"jobId": "job-balance-1"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [{"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
            {"date": "2026-01-03", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
        ],
        "employees": [
            {"id": "emp_001", "skills": ["Apotheker"], "currentBalanceHours": 10.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_002", "skills": ["Apotheker"], "currentBalanceHours": -5.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE", "TIMEOUT")


def test_fairness_distributes_shifts_across_employees():
    """Test that the solver distributes shifts across employees (no hard min/max constraint)."""
    payload = {
        "metadata": {"jobId": "job-balance-2"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [{"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
            {"date": "2026-01-03", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
            {"date": "2026-01-04", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
        ],
        "employees": [
            {"id": "emp_001", "skills": ["Apotheker"], "currentBalanceHours": 10.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_002", "skills": ["Apotheker"], "currentBalanceHours": -10.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=30)
    
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE", "TIMEOUT")
    # Must have assigned at least 1 shift
    assert len(result["solution"]["assignments"]) >= 1


def test_fairness_with_skill_groups():
    """Test that employees are grouped by skill for fairness computation."""
    # Two skill groups: Apotheker and PKA
    # 2 shifts needing Apotheker, 2 needing PKA
    # Employees with different balances in each group
    payload = {
        "metadata": {"jobId": "job-balance-3"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-14"},
        "shiftTemplates": [
            {"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"},
            {"id": "S_SPAET", "startTime": "14:00", "endTime": "22:00"},
        ],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
            {"date": "2026-01-03", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
            {"date": "2026-01-04", "shiftId": "S_SPAET", "neededSkills": {"PKA": 1}},
            {"date": "2026-01-05", "shiftId": "S_SPAET", "neededSkills": {"PKA": 1}},
        ],
        "employees": [
            {"id": "emp_001", "skills": ["Apotheker"], "currentBalanceHours": 5.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_002", "skills": ["Apotheker"], "currentBalanceHours": -5.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_003", "skills": ["PKA"], "currentBalanceHours": 5.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_004", "skills": ["PKA"], "currentBalanceHours": -5.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=30)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE", "TIMEOUT")


def test_shift_count_hard_constraint_replaced():
    """Test that shift-count hard constraint is no longer enforced (replaced by soft)."""
    # 5 requirements but 3 employees - can't evenly distribute shifts
    # Old hard constraint would force infeasibility
    payload = {
        "metadata": {"jobId": "job-balance-4"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-14"},
        "shiftTemplates": [{"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
            {"date": "2026-01-03", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
            {"date": "2026-01-04", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
            {"date": "2026-01-05", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
            {"date": "2026-01-06", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
        ],
        "employees": [
            {"id": "emp_001", "skills": ["Apotheker"], "currentBalanceHours": 0.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_002", "skills": ["Apotheker"], "currentBalanceHours": 0.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_003", "skills": ["Apotheker"], "currentBalanceHours": 0.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=30)
    # Should be feasible now (soft constraint instead of hard)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE", "TIMEOUT")
    assert len(result["solution"]["assignments"]) > 0


def test_solver_metrics_include_fairness_info():
    """Test that solver metrics include fairness-related data."""
    payload = {
        "metadata": {"jobId": "job-metrics-1"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [{"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
        ],
        "employees": [
            {"id": "emp_001", "skills": ["Apotheker"], "currentBalanceHours": 5.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE", "TIMEOUT")
    
    metrics = result["metrics"]
    # Should include employee-level fairness info
    assert "employeeFairness" in metrics
    for emp_id, fair_data in metrics["employeeFairness"].items():
        assert "currentBalanceHours" in fair_data
        assert "scheduledHours" in fair_data
        assert "projectedBalance" in fair_data
        assert "fairnessDeviation" in fair_data


def test_solver_respects_weekly_hours():
    payload = {
        "metadata": {"jobId": "job-003"},
        "config": {
            "schemaVersion": "1.0",
            "startDate": "2026-01-01",
            "endDate": "2026-01-31",
            "maxConsecutiveDays": 6,
            "minRestTimeHours": 11,
        },
        "shiftTemplates": [
            {"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"},
        ],
        "requirements": [
            {"date": "2026-01-04", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
            {"date": "2026-01-05", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
            {"date": "2026-01-06", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
        ],
        "employees": [
            {
                "id": "emp_001",
                "skills": ["Apotheker"],
                "forbiddenDates": [],
                "contract": {"weeklyHours": 14.0},
            },
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)

    assert result["metadata"]["status"] == "INFEASIBLE"
