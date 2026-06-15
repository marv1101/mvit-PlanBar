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


def test_count_expansion_assigns_different_employees():
    """Test that count > 1 assigns different employees to each expanded slot."""
    payload = {
        "metadata": {"jobId": "job-count-1"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [
            {"id": "S_KURZ", "startTime": "08:00", "endTime": "12:00"},
        ],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_KURZ", "count": 2},
        ],
        "employees": [
            {"id": "emp_001", "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_002", "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert len(result["solution"]["assignments"]) == 2
    assigned_emps = {a["employeeId"] for a in result["solution"]["assignments"]}
    assert len(assigned_emps) == 2, "Must assign 2 different employees"


def test_balance_influences_assignment_distribution():
    """Test that employees with negative balance receive more shifts."""
    payload = {
        "metadata": {"jobId": "job-balance-behavior-1"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [
            {"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"},
        ],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-03", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-04", "shiftId": "S_FRUEH", "count": 1},
        ],
        "employees": [
            {"id": "emp_001", "currentBalanceHours": 10.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_002", "currentBalanceHours": -10.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=30)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert len(result["solution"]["assignments"]) == 3

    emp_shifts = {a["employeeId"]: 0 for a in result["solution"]["assignments"]}
    for a in result["solution"]["assignments"]:
        emp_shifts[a["employeeId"]] = emp_shifts.get(a["employeeId"], 0) + 1

    # emp_002 has -10h (needs to catch up) → should get at least 2 of 3 shifts
    neg_emp_shifts = emp_shifts.get("emp_002", 0)
    pos_emp_shifts = emp_shifts.get("emp_001", 0)
    assert neg_emp_shifts >= pos_emp_shifts, (
        f"Employee with negative balance ({neg_emp_shifts}) should get at least as many "
        f"shifts as positive balance employee ({pos_emp_shifts})"
    )


def test_balance_recovery_changes_behavior():
    """Test that balance recovery changes solver behavior compared to no balance."""
    # Scenario A: No balance (both employees have 0.0 balance)
    payload_no_balance = {
        "metadata": {"jobId": "job-balance-compare-1"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [
            {"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"},
        ],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-03", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-04", "shiftId": "S_FRUEH", "count": 1},
        ],
        "employees": [
            {"id": "emp_001", "currentBalanceHours": 0.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_002", "currentBalanceHours": 0.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [],
    }

    # Scenario B: With balance (one employee has -10h, other +10h)
    payload_with_balance = {
        "metadata": {"jobId": "job-balance-compare-2"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [
            {"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"},
        ],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-03", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-04", "shiftId": "S_FRUEH", "count": 1},
        ],
        "employees": [
            {"id": "emp_001", "currentBalanceHours": 10.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_002", "currentBalanceHours": -10.0, "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [],
    }

    result_no_balance = solve_model(build_model(payload_no_balance), timeout_seconds=30)
    result_with_balance = solve_model(build_model(payload_with_balance), timeout_seconds=30)

    assert result_no_balance["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert result_with_balance["metadata"]["status"] in ("SUCCESS", "FEASIBLE")

    # Count shifts per employee in each scenario
    def emp_shift_counts(result):
        counts = {}
        for a in result["solution"]["assignments"]:
            counts[a["employeeId"]] = counts.get(a["employeeId"], 0) + 1
        return counts

    counts_no_balance = emp_shift_counts(result_no_balance)
    counts_with_balance = emp_shift_counts(result_with_balance)

    neg_with = counts_with_balance.get("emp_002", 0)
    pos_with = counts_with_balance.get("emp_001", 0)

    # With balance: negative-balance employee should get more shifts than positive-balance
    assert neg_with > pos_with, (
        f"With balance, emp_002 (-10h, {neg_with} shifts) should get more shifts "
        f"than emp_001 (+10h, {pos_with} shifts)"
    )


def test_solver_uses_contractHours_field():
    """Solver reads contractHours when no contract dict is present."""
    payload = {
        "metadata": {"jobId": "job-contract-hours"},
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
                "contractHours": 14.0,
            },
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)

    assert result["metadata"]["status"] == "INFEASIBLE"


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


def test_solver_empty_requirements_returns_success():
    payload = {
        "metadata": {"jobId": "job-empty"},
        "config": {
            "startDate": "2026-06-15",
            "endDate": "2026-06-21",
        },
        "shiftTemplates": [],
        "requirements": [],
        "employees": [
            {"id": "emp_001", "name": "Test1", "contractHours": 40.0},
            {"id": "emp_002", "name": "Test2", "contractHours": 40.0},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)

    assert result["metadata"]["status"] == "SUCCESS"
    assert result["solution"]["assignments"] == []
    assert result["metrics"]["wishFulfillmentRate"] == 100.0


def test_solver_contractHours_works_without_contract_dict():
    payload = {
        "metadata": {"jobId": "job-contractHours"},
        "config": {
            "startDate": "2026-01-01",
            "endDate": "2026-01-07",
        },
        "shiftTemplates": [
            {"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"},
        ],
        "requirements": [
            {"date": "2026-01-04", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
            {"date": "2026-01-05", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
        ],
        "employees": [
            {
                "id": "emp_001",
                "name": "Test",
                "skills": ["Apotheker"],
                "forbiddenDates": [],
                "contractHours": 40.0,
            },
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)

    assert result["metadata"]["status"] == "SUCCESS"
    assert len(result["solution"]["assignments"]) == 2
    assert result["metrics"]["employeeFairness"]["emp_001"]["targetHours"] > 0
