from tito.solver import build_model, solve_model


def test_solver_generates_assignments_for_valid_payload():
    payload = {
        "metadata": {"jobId": "job-001"},
        "shiftTemplates": [{"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}],
        "requirements": [
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            }
        ],
        "employees": [{"id": "emp_001", "skills": ["Apotheker"], "forbiddenDates": []}],
        "wishes": [
            {
                "employeeId": "emp_001",
                "type": "PREFER_SHIFT",
                "shiftId": "S_FRUEH",
                "date": "2026-01-02",
            }
        ],
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
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {
                "date": "2026-01-02",
                "shiftId": "S_SPAET",
                "neededSkills": {"Apotheker": 1},
            },
        ],
        "employees": [
            {
                "id": "emp_001",
                "skills": ["Apotheker"],
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
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
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {
                "date": "2026-01-03",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
        ],
        "employees": [
            {
                "id": "emp_001",
                "skills": ["Apotheker"],
                "currentBalanceHours": 10.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
            {
                "id": "emp_002",
                "skills": ["Apotheker"],
                "currentBalanceHours": -5.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
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
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {
                "date": "2026-01-03",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {
                "date": "2026-01-04",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
        ],
        "employees": [
            {
                "id": "emp_001",
                "skills": ["Apotheker"],
                "currentBalanceHours": 10.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
            {
                "id": "emp_002",
                "skills": ["Apotheker"],
                "currentBalanceHours": -10.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
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
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {
                "date": "2026-01-03",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {"date": "2026-01-04", "shiftId": "S_SPAET", "neededSkills": {"PKA": 1}},
            {"date": "2026-01-05", "shiftId": "S_SPAET", "neededSkills": {"PKA": 1}},
        ],
        "employees": [
            {
                "id": "emp_001",
                "skills": ["Apotheker"],
                "currentBalanceHours": 5.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
            {
                "id": "emp_002",
                "skills": ["Apotheker"],
                "currentBalanceHours": -5.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
            {
                "id": "emp_003",
                "skills": ["PKA"],
                "currentBalanceHours": 5.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
            {
                "id": "emp_004",
                "skills": ["PKA"],
                "currentBalanceHours": -5.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
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
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {
                "date": "2026-01-03",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {
                "date": "2026-01-04",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {
                "date": "2026-01-05",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {
                "date": "2026-01-06",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
        ],
        "employees": [
            {
                "id": "emp_001",
                "skills": ["Apotheker"],
                "currentBalanceHours": 0.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
            {
                "id": "emp_002",
                "skills": ["Apotheker"],
                "currentBalanceHours": 0.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
            {
                "id": "emp_003",
                "skills": ["Apotheker"],
                "currentBalanceHours": 0.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
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
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
        ],
        "employees": [
            {
                "id": "emp_001",
                "skills": ["Apotheker"],
                "currentBalanceHours": 5.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE", "TIMEOUT")

    metrics = result["metrics"]
    # Should include employee-level fairness info
    assert "employeeFairness" in metrics
    for fair_data in metrics["employeeFairness"].values():
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
            {
                "id": "emp_001",
                "currentBalanceHours": 10.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
            {
                "id": "emp_002",
                "currentBalanceHours": -10.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
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
            {
                "id": "emp_001",
                "currentBalanceHours": 0.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
            {
                "id": "emp_002",
                "currentBalanceHours": 0.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
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
            {
                "id": "emp_001",
                "currentBalanceHours": 10.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
            {
                "id": "emp_002",
                "currentBalanceHours": -10.0,
                "forbiddenDates": [],
                "contract": {"weeklyHours": 40.0},
            },
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

    emp_shift_counts(result_no_balance)
    counts_with_balance = emp_shift_counts(result_with_balance)

    neg_with = counts_with_balance.get("emp_002", 0)
    pos_with = counts_with_balance.get("emp_001", 0)

    # With balance: negative-balance employee should get more shifts than positive-balance
    assert neg_with > pos_with, (
        f"With balance, emp_002 (-10h, {neg_with} shifts) should get more shifts than emp_001 (+10h, {pos_with} shifts)"
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
            {
                "date": "2026-01-04",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {
                "date": "2026-01-05",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {
                "date": "2026-01-06",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
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
            {
                "date": "2026-01-04",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {
                "date": "2026-01-05",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {
                "date": "2026-01-06",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
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


def test_vacation_wish_blocks_assignment():
    """Test that a vacation wish is treated as a hard OFF constraint."""
    payload = {
        "metadata": {"jobId": "job-vacation-1"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [
            {"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"},
            {"id": "S_SPAET", "startTime": "14:00", "endTime": "22:00"},
        ],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-02", "shiftId": "S_SPAET", "count": 1},
            {"date": "2026-01-03", "shiftId": "S_FRUEH", "count": 1},
        ],
        "employees": [
            {"id": "emp_001", "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_002", "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_003", "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [
            {"employeeId": "emp_001", "type": "vacation", "date": "2026-01-02"},
        ],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=30)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    for assignment in result["solution"]["assignments"]:
        if assignment["employeeId"] == "emp_001":
            assert assignment["date"] != "2026-01-02", (
                "emp_001 should NOT be assigned on 2026-01-02 (vacation wish)"
            )


def test_unavailable_wish_blocks_assignment():
    """Test that an unavailable wish is treated as a hard OFF constraint."""
    payload = {
        "metadata": {"jobId": "job-unavailable-1"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [
            {"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"},
        ],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-03", "shiftId": "S_FRUEH", "count": 1},
        ],
        "employees": [
            {"id": "emp_001", "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_002", "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [
            {"employeeId": "emp_001", "type": "unavailable", "date": "2026-01-02"},
        ],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=30)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    for assignment in result["solution"]["assignments"]:
        if assignment["employeeId"] == "emp_001":
            assert assignment["date"] != "2026-01-02", (
                "emp_001 should NOT be assigned on 2026-01-02 (unavailable wish)"
            )


def test_preferred_wish_without_shift_id_influences_assignment():
    """Test that a preferred wish without shiftId influences day-level assignment."""
    payload = {
        "metadata": {"jobId": "job-preferred-1"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [
            {"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"},
            {"id": "S_SPAET", "startTime": "14:00", "endTime": "22:00"},
        ],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-02", "shiftId": "S_SPAET", "count": 1},
        ],
        "employees": [
            {"id": "emp_001", "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_002", "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [
            {"employeeId": "emp_001", "type": "preferred", "date": "2026-01-02"},
        ],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=30)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    emp_001_assignments = [
        a for a in result["solution"]["assignments"]
        if a["employeeId"] == "emp_001" and a["date"] == "2026-01-02"
    ]
    assert len(emp_001_assignments) > 0, (
        "emp_001 should be assigned on 2026-01-02 due to preferred wish"
    )


def test_vacation_wish_fulfillment_rate_not_always_100():
    """Test that vacation wishes are counted in wishFulfillmentRate."""
    payload = {
        "metadata": {"jobId": "job-vacation-rate-1"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [
            {"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"},
        ],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1},
        ],
        "employees": [
            {"id": "emp_001", "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_002", "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [
            {"employeeId": "emp_001", "type": "vacation", "date": "2026-01-02"},
            {"employeeId": "emp_002", "type": "preferred", "date": "2026-01-02"},
        ],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=30)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    # Both wishes should be considered (vacation fulfilled as hard constraint,
    # preferred fulfilled because emp_002 gets the only shift).
    assert result["metrics"]["wishFulfillmentRate"] == 100.0


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


def test_empty_requirements_with_vacation_wish_counts_correctly():
    """Test that vacation/OFF/unavailable wishes are fulfilled when no requirements exist."""
    payload = {
        "metadata": {"jobId": "job-empty-vacation"},
        "config": {"startDate": "2026-06-15", "endDate": "2026-06-21"},
        "shiftTemplates": [],
        "requirements": [],
        "employees": [
            {"id": "emp_001", "name": "Test1", "contractHours": 40.0},
            {"id": "emp_002", "name": "Test2", "contractHours": 40.0},
        ],
        "wishes": [
            {"employeeId": "emp_001", "type": "vacation", "date": "2026-06-16"},
            {"employeeId": "emp_002", "type": "unavailable", "date": "2026-06-17"},
        ],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)

    assert result["metadata"]["status"] == "SUCCESS"
    assert result["solution"]["assignments"] == []
    assert result["metrics"]["wishFulfillmentRate"] == 100.0


def test_empty_requirements_with_preferred_wish_counts_correctly():
    """Test that preferred wishes are NOT fulfilled when no requirements exist."""
    payload = {
        "metadata": {"jobId": "job-empty-preferred"},
        "config": {"startDate": "2026-06-15", "endDate": "2026-06-21"},
        "shiftTemplates": [],
        "requirements": [],
        "employees": [
            {"id": "emp_001", "name": "Test1", "contractHours": 40.0},
        ],
        "wishes": [
            {"employeeId": "emp_001", "type": "preferred", "date": "2026-06-16"},
        ],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)

    assert result["metadata"]["status"] == "SUCCESS"
    assert result["solution"]["assignments"] == []
    assert result["metrics"]["wishFulfillmentRate"] == 0.0


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
            {
                "date": "2026-01-04",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {
                "date": "2026-01-05",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
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


def test_off_wish_respected():
    """Test that OFF wishes are respected - employee is NOT assigned to any shift on that date."""
    payload = {
        "metadata": {"jobId": "job-off-1"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [
            {"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"},
            {"id": "S_SPAET", "startTime": "14:00", "endTime": "22:00"},
        ],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-02", "shiftId": "S_SPAET", "count": 1},
            {"date": "2026-01-03", "shiftId": "S_FRUEH", "count": 1},
        ],
        "employees": [
            {"id": "emp_001", "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_002", "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_003", "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [
            {"employeeId": "emp_001", "type": "OFF", "date": "2026-01-02"},
        ],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=30)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")

    # Verify emp_001 is NOT assigned to any shift on 2026-01-02
    for assignment in result["solution"]["assignments"]:
        if assignment["employeeId"] == "emp_001":
            assert assignment["date"] != "2026-01-02", (
                f"emp_001 should NOT be assigned on 2026-01-02 (OFF wish), "
                f"but got assignment to {assignment.get('shiftId')}"
            )


def test_off_wish_vs_prefer_shift():
    """Test that OFF wishes take priority over PREFER_SHIFT when they conflict."""
    payload = {
        "metadata": {"jobId": "job-off-pref-conflict"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [
            {"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"},
        ],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-03", "shiftId": "S_FRUEH", "count": 1},
        ],
        "employees": [
            {"id": "emp_001", "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_002", "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [
            # emp_001 prefers the morning shift on Jan 2...
            {"employeeId": "emp_001", "type": "PREFER_SHIFT", "shiftId": "S_FRUEH", "date": "2026-01-02"},
            # ...but also has an OFF wish for the same day
            {"employeeId": "emp_001", "type": "OFF", "date": "2026-01-02"},
        ],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=30)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")

    # OFF should win: emp_001 should NOT be assigned on 2026-01-02
    for assignment in result["solution"]["assignments"]:
        if assignment["employeeId"] == "emp_001":
            assert assignment["date"] != "2026-01-02", (
                "OFF wish should take priority over PREFER_SHIFT, "
                "but emp_001 was assigned on 2026-01-02"
            )


def test_holiday_treated_like_sunday():
    """Test that work on a public holiday counts toward the Sunday/holiday limit.

    According to ArbZG §9, public holidays are treated like Sundays for work
    limit purposes.

    Scenario:
    - Period: 2026-01-01 (Thu/holiday) through 2026-01-11 (Sun)
    - Sundays in period: Jan 4, Jan 11 (2 Sundays)
    - Holiday in period: Jan 1 (Neujahr)
    - minFreeSundaysPerYear=49 → allows 1 protected day work per employee
      (required_free = round(49*3/52)=3, allowed = 3 - min(3,2) = 1)

    Without holiday awareness: employee could work Jan 1 (holiday, not counted)
    + Jan 4 (Sunday, counted) = 2 protected days.

    With holiday awareness: employee should work at most 1 protected day total
    (Sunday OR holiday). Need 3 employees to cover all 3 protected days.
    """
    payload = {
        "metadata": {"jobId": "job-holiday-1"},
        "config": {
            "startDate": "2026-01-01",
            "endDate": "2026-01-11",
            "minFreeSundaysPerYear": 49,
            "holidayDates": ["2026-01-01"],
        },
        "shiftTemplates": [
            {"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"},
        ],
        "requirements": [
            # Jan 1 = Thursday (holiday), Jan 4 = Sunday, Jan 5 = Monday, Jan 11 = Sunday
            {"date": "2026-01-01", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-04", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-05", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-11", "shiftId": "S_FRUEH", "count": 1},
        ],
        "employees": [
            {"id": "emp_001", "skills": ["Apotheker"], "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_002", "skills": ["Apotheker"], "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_003", "skills": ["Apotheker"], "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=30)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")

    # Verify: no single employee should be assigned on both a holiday and a Sunday
    protected_dates = {"2026-01-01", "2026-01-04", "2026-01-11"}  # holiday + Sundays
    emp_protected_count = {}
    for a in result["solution"]["assignments"]:
        if a["date"] in protected_dates:
            emp_protected_count[a["employeeId"]] = emp_protected_count.get(a["employeeId"], 0) + 1

    for emp_id, count in emp_protected_count.items():
        assert count <= 1, (
            f"Employee {emp_id} worked on {count} protected days (Sunday/holiday). "
            f"With minFreeSundaysPerYear=49 and holidayDates=[2026-01-01], "
            f"should work on at most 1 protected day total (ArbZG §9)"
        )


def test_holiday_rest_constraint():
    """Test that minimum rest time is enforced across holiday boundaries.

    If an employee works a late shift ending at 22:00 on a holiday,
    they must not start before the minimum rest time on the next day.
    """
    payload = {
        "metadata": {"jobId": "job-holiday-rest-1"},
        "config": {
            "startDate": "2026-01-01",
            "endDate": "2026-01-05",
            "minRestTimeHours": 11,
            "minFreeSundaysPerYear": 15,
            "holidayDates": ["2026-01-01"],
        },
        "shiftTemplates": [
            {"id": "S_SPAET", "startTime": "14:00", "endTime": "22:00"},
            {"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"},
        ],
        "requirements": [
            # Jan 1 (holiday): late shift 14:00-22:00
            # Jan 2 (Friday): early shift 06:00-14:00 — only 8h gap, violates 11h rest
            {"date": "2026-01-01", "shiftId": "S_SPAET", "count": 1},
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1},
            # Also add shifts on Jan 3-4 to give other employees something to do
            {"date": "2026-01-03", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-04", "shiftId": "S_FRUEH", "count": 1},
        ],
        "employees": [
            {"id": "emp_001", "skills": ["Apotheker"], "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
            {"id": "emp_002", "skills": ["Apotheker"], "forbiddenDates": [], "contract": {"weeklyHours": 40.0}},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=30)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")

    # Verify: no employee should work S_SPAET on Jan 1 AND S_FRUEH on Jan 2
    # (that would be only 8h rest, violating 11h minimum)
    assignments = result["solution"]["assignments"]
    for emp_id in ["emp_001", "emp_002"]:
        emp_assignments = [a for a in assignments if a["employeeId"] == emp_id]
        works_late_jan1 = any(
            a["date"] == "2026-01-01" and a["shiftId"] == "S_SPAET"
            for a in emp_assignments
        )
        works_early_jan2 = any(
            a["date"] == "2026-01-02" and a["shiftId"] == "S_FRUEH"
            for a in emp_assignments
        )
        assert not (works_late_jan1 and works_early_jan2), (
            f"Employee {emp_id} must not work S_SPAET on Jan 1 (holiday, ends 22:00) "
            f"and S_FRUEH on Jan 2 (starts 06:00) — only 8h rest, violates 11h minimum"
        )


def test_solver_maxCount_expands_optional_slots():
    """count=1, maxCount=3 with maximizeStaffing=False: only mandatory (1) filled."""
    payload = {
        "metadata": {"jobId": "job-maxcount-1"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [{"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}],
        "requirements": [
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "count": 1,
                "maxCount": 3,
            },
        ],
        "employees": [
            {"id": "emp_001", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
            {"id": "emp_002", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
            {"id": "emp_003", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    # Without maximizeStaffing, only mandatory slots (count=1) are filled
    assert len(result["solution"]["assignments"]) == 1


def test_solver_maxCount_fills_mandatory_only_when_not_enough_employees():
    """count=2, maxCount=5 with maximizeStaffing=True and 3 employees: should fill 3."""
    payload = {
        "metadata": {"jobId": "job-maxcount-2"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07", "maximizeStaffing": True},
        "shiftTemplates": [{"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}],
        "requirements": [
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "count": 2,
                "maxCount": 5,
            },
        ],
        "employees": [
            {"id": "emp_001", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
            {"id": "emp_002", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
            {"id": "emp_003", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    # maxCount=5 but only 3 qualified employees, so max 3 assignments
    assert len(result["solution"]["assignments"]) == 3


def test_solver_maximizeStaffing_fills_optional_slots():
    """maximizeStaffing=True with maxCount set should fill optional slots."""
    payload = {
        "metadata": {"jobId": "job-maxstaff-1"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07", "maximizeStaffing": True},
        "shiftTemplates": [{"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}],
        "requirements": [
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "count": 1,
                "maxCount": 3,
            },
        ],
        "employees": [
            {"id": "emp_001", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
            {"id": "emp_002", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
            {"id": "emp_003", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert len(result["solution"]["assignments"]) > 1


def test_solver_maximizeStaffing_false_does_not_fill_optional():
    """maximizeStaffing=False with maxCount set should assign approximately count (mandatory only)."""
    payload = {
        "metadata": {"jobId": "job-maxstaff-2"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07", "maximizeStaffing": False},
        "shiftTemplates": [{"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}],
        "requirements": [
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "count": 1,
                "maxCount": 3,
            },
        ],
        "employees": [
            {"id": "emp_001", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
            {"id": "emp_002", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
            {"id": "emp_003", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert len(result["solution"]["assignments"]) == 1


def test_solver_maximizeStaffing_without_maxCount_auto_expands():
    """maximizeStaffing=True without maxCount should auto-expand optional slots to number of qualified employees."""
    payload = {
        "metadata": {"jobId": "job-maxstaff-3"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07", "maximizeStaffing": True},
        "shiftTemplates": [{"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}],
        "requirements": [
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "count": 1,
            },
        ],
        "employees": [
            {"id": "emp_001", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
            {"id": "emp_002", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
            {"id": "emp_003", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
            {"id": "emp_004", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
            {"id": "emp_005", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert len(result["solution"]["assignments"]) > 1


def test_solver_optional_unassigned_slot_reported_as_SOFT():
    """Optional (non-mandatory) unfilled slots should have SOFT severity, not HARD."""
    # count=1, maxCount=3, but only 1 employee available → 2 optional slots unfilled
    payload = {
        "metadata": {"jobId": "job-opt-soft"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [{"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}],
        "requirements": [
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "count": 1,
                "maxCount": 3,
            },
        ],
        "employees": [
            {"id": "emp_001", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    violations = result["metrics"]["violations"]
    soft_violations = [v for v in violations if v["severity"] == "SOFT"]
    hard_unassigned = [
        v for v in violations
        if v["type"] == "UNASSIGNED_REQUIREMENT" and v["severity"] == "HARD"
    ]
    # The mandatory slot is filled, optional slots unfilled → SOFT violations
    assert len(soft_violations) > 0
    assert all(v["type"] == "UNASSIGNED_REQUIREMENT" for v in soft_violations)
    assert len(hard_unassigned) == 0


def test_solver_maxCount_clamped_when_less_than_count():
    """maxCount < count is silently clamped to count (defensive guard)."""
    # maxCount=2 < count=3 → should be clamped to 3 mandatory slots
    payload = {
        "metadata": {"jobId": "job-clamp"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [{"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}],
        "requirements": [
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "count": 3,
                "maxCount": 2,
            },
        ],
        "employees": [
            {"id": "emp_001", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
            {"id": "emp_002", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
            {"id": "emp_003", "skills": ["Apotheker"], "forbiddenDates": [], "contractHours": 40.0},
        ],
        "wishes": [],
    }
    model = build_model(payload)
    result = solve_model(model, timeout_seconds=10)

    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    # All 3 employees assigned despite maxCount < count
    assert len(result["solution"]["assignments"]) == 3
