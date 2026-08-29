from datetime import datetime, timedelta, timezone

import pytest
from tito.schema import Employee, JobPayload, validate_job_payload


def test_schema_accepts_valid_payload():
    """Test with a complete valid payload."""
    today = datetime.now(tz=timezone.utc).date()
    start_date = today.strftime("%Y-%m-%d")
    end_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")

    payload = {
        "metadata": {
            "jobId": "job-schema-1",
            "tenantId": 1,
            "priority": 1,
            "timestamp": "2026-05-08T10:00:00Z",
        },
        "config": {
            "schemaVersion": "1.0",
            "startDate": start_date,
            "endDate": end_date,
            "maxConsecutiveDays": 6,
            "minRestTimeHours": 11,
        },
        "shiftTemplates": [
            {
                "id": "S_FRUEH",
                "name": "Frühschicht",
                "startTime": "06:00",
                "endTime": "14:00",
            }
        ],
        "requirements": [{"shiftTemplateId": "S_FRUEH", "date": start_date, "count": 1}],
        "employees": [{"id": "E001", "name": "Max Mustermann", "contractHours": 40.0}],
        "wishes": [{"employeeId": "E001", "date": start_date, "type": "OFF"}],
    }

    result = validate_job_payload(payload)
    assert isinstance(result, JobPayload)
    assert result.metadata.jobId == "job-schema-1"
    assert result.metadata.tenantId == 1


def test_schema_accepts_legacy_payload_fields():
    """Test that legacy field names are accepted and normalized."""
    payload = {
        "metadata": {"tenantId": 1, "priority": 2, "timestamp": "2026-05-08T10:00:00Z"},
        "config": {
            "schemaVersion": "1.0",
            "startDate": "2026-01-01",
            "endDate": "2026-01-07",
        },
        "shiftTemplates": [
            {
                "id": "S_FRUEH",
                "name": "Frühschicht",
                "startTime": "06:00",
                "endTime": "14:00",
            }
        ],
        "requirements": [
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            }
        ],
        "employees": [
            {
                "id": "E001",
                "name": "Max Mustermann",
                "contract": {"weeklyHours": 40.0, "employmentType": "Apotheker"},
                "skills": ["Apotheker"],
                "forbiddenDates": [],
            }
        ],
        "wishes": [
            {
                "employeeId": "E001",
                "type": "PREFER_SHIFT",
                "shiftId": "S_FRUEH",
                "date": "2026-01-02",
                "weight": 2,
                "comment": "Frühschicht bevorzugt",
            }
        ],
    }

    result = validate_job_payload(payload)
    assert result.metadata.jobId is None
    assert result.requirements[0].shiftTemplateId == "S_FRUEH"
    assert result.requirements[0].count == 1
    assert result.requirements[0].skills == ["Apotheker"]
    assert result.wishes[0].shiftTemplateId == "S_FRUEH"
    assert result.wishes[0].priority == 2


def test_schema_rejects_missing_required_fields():
    """Test that missing required fields are rejected."""
    payload = {"metadata": {"jobId": "job-schema-2"}}

    with pytest.raises(ValueError):
        validate_job_payload(payload)


def test_schema_rejects_invalid_date_format():
    """Test that invalid date formats are rejected."""
    payload = {
        "metadata": {"jobId": "job-schema-3", "tenantId": 1},
        "config": {
            "schemaVersion": "1.0",
            "startDate": "invalid-date",
            "endDate": "2026-01-31",
        },
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
    }

    with pytest.raises(ValueError):
        validate_job_payload(payload)


def test_schema_rejects_invalid_time_format():
    """Test that invalid time formats are rejected."""
    payload = {
        "metadata": {"jobId": "job-schema-4", "tenantId": 1},
        "config": {
            "schemaVersion": "1.0",
            "startDate": "2026-01-01",
            "endDate": "2026-01-31",
        },
        "shiftTemplates": [
            {
                "id": "S_FRUEH",
                "name": "Frühschicht",
                "startTime": "invalid-time",
                "endTime": "14:00",
            }
        ],
        "requirements": [],
        "employees": [],
    }

    with pytest.raises(ValueError):
        validate_job_payload(payload)


def test_schema_ignores_unknown_fields():
    """Test that unknown fields are silently ignored (extra='ignore')."""
    payload = {
        "metadata": {
            "jobId": "job-schema-5",
            "tenantId": 1,
            "tenant_id": 1,
        },
        "config": {
            "schemaVersion": "1.0",
            "startDate": "2026-01-01",
            "endDate": "2026-01-31",
        },
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
        "unknown_field": "should_be_ignored",
    }

    result = validate_job_payload(payload)
    assert result is not None
    assert result.metadata.tenantId == 1


def test_schema_validates_date_range():
    """Test that startDate must be before endDate."""
    payload = {
        "metadata": {"jobId": "job-schema-6", "tenantId": 1},
        "config": {
            "schemaVersion": "1.0",
            "startDate": "2026-01-31",
            "endDate": "2026-01-01",
        },
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
    }

    with pytest.raises(ValueError):
        validate_job_payload(payload)


def test_schema_validates_references():
    """Test that references to non-existent shifts/employees are rejected."""
    payload = {
        "metadata": {"jobId": "job-schema-7", "tenantId": 1},
        "config": {
            "schemaVersion": "1.0",
            "startDate": "2026-01-01",
            "endDate": "2026-01-31",
        },
        "shiftTemplates": [],
        "requirements": [{"shiftTemplateId": "NON_EXISTENT", "date": "2026-01-01", "count": 1}],
        "employees": [],
    }

    with pytest.raises(ValueError):
        validate_job_payload(payload)


def test_employee_accepts_current_balance_hours():
    """Test that Employee schema accepts currentBalanceHours field."""
    emp = Employee(id="E001", name="Test", currentBalanceHours=12.5)
    assert emp.currentBalanceHours == 12.5


def test_employee_defaults_current_balance_hours():
    """Test that currentBalanceHours defaults to 0.0."""
    emp = Employee(id="E001", name="Test")
    assert emp.currentBalanceHours == 0.0


def test_employee_extracts_current_balance_from_contract():
    """Test backward compat: extract currentBalanceHours from contract dict."""
    emp = Employee(
        id="E001",
        name="Test",
        contract={"weeklyHours": 40.0, "currentBalanceHours": 5.5},
    )
    assert emp.currentBalanceHours == 5.5


def test_employee_accepts_current_balance_via_payload():
    """Test that full payload validation accepts currentBalanceHours."""
    payload = {
        "metadata": {"tenantId": 1},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [],
        "requirements": [],
        "employees": [{"id": "E001", "name": "Test", "currentBalanceHours": 3.5}],
    }
    result = validate_job_payload(payload)
    assert result.employees[0].currentBalanceHours == 3.5


def test_employee_contractHours_reverse_normalizer():
    """Employee with contractHours (no contract dict) builds contract.weeklyHours."""
    emp = Employee(id="E001", name="Test", contractHours=20.0)
    assert emp.contractHours == 20.0
    assert emp.contract == {"weeklyHours": 20.0}


def test_employee_contractHours_with_existing_contract_not_overwritten():
    """contract dict takes precedence when both are provided."""
    emp = Employee(id="E001", name="Test", contractHours=20.0, contract={"weeklyHours": 35.0})
    assert emp.contractHours == 20.0
    assert emp.contract == {"weeklyHours": 35.0}


def test_schema_with_minimal_required_fields():
    """Test that minimal valid payloads work."""
    payload = {
        "metadata": {"jobId": "job-schema-8", "tenantId": 1},
        "config": {
            "schemaVersion": "1.0",
            "startDate": "2026-01-01",
            "endDate": "2026-01-31",
        },
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
    }

    result = validate_job_payload(payload)
    assert result.metadata.jobId == "job-schema-8"
    assert result.config.schemaVersion == "1.0"


# ============================================================================
# maxCount (maximale Belegung) tests
# ============================================================================


def test_requirement_accepts_maxCount():
    """Requirement with maxCount is valid."""
    payload = {
        "metadata": {"tenantId": 1},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [{"id": "S1", "name": "Früh", "startTime": "06:00", "endTime": "14:00"}],
        "requirements": [
            {"shiftTemplateId": "S1", "date": "2026-01-02", "count": 2, "maxCount": 5}
        ],
        "employees": [],
    }
    result = validate_job_payload(payload)
    assert result.requirements[0].maxCount == 5


def test_requirement_maxCount_none_by_default():
    """Requirement without maxCount defaults to None."""
    payload = {
        "metadata": {"tenantId": 1},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [{"id": "S1", "name": "Früh", "startTime": "06:00", "endTime": "14:00"}],
        "requirements": [
            {"shiftTemplateId": "S1", "date": "2026-01-02", "count": 2}
        ],
        "employees": [],
    }
    result = validate_job_payload(payload)
    assert result.requirements[0].maxCount is None


def test_config_accepts_maximizeStaffing():
    """Config with maximizeStaffing=True is valid."""
    payload = {
        "metadata": {"tenantId": 1},
        "config": {
            "startDate": "2026-01-01",
            "endDate": "2026-01-07",
            "maximizeStaffing": True,
        },
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
    }
    result = validate_job_payload(payload)
    assert result.config.maximizeStaffing is True


def test_config_maximizeStaffing_defaults_false():
    """Config without maximizeStaffing defaults to False."""
    payload = {
        "metadata": {"tenantId": 1},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
    }
    result = validate_job_payload(payload)
    assert result.config.maximizeStaffing is False
