import pytest
from datetime import datetime, timedelta
from tito.schema import (
    validate_job_payload, JobPayload, Metadata, Config, 
    ShiftTemplate, Requirement, Employee, Wish
)


def test_schema_accepts_valid_payload():
    """Test with a complete valid payload."""
    today = datetime.now().date()
    start_date = today.strftime("%Y-%m-%d")
    end_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")
    
    payload = {
        "metadata": {
            "jobId": "job-schema-1",
            "tenantId": 1,
            "priority": 1,
            "timestamp": "2026-05-08T10:00:00Z"
        },
        "config": {
            "schemaVersion": "1.0",
            "startDate": start_date,
            "endDate": end_date,
            "maxConsecutiveDays": 6,
            "minRestTimeHours": 11
        },
        "shiftTemplates": [
            {
                "id": "S_FRUEH",
                "name": "Frühschicht",
                "startTime": "06:00",
                "endTime": "14:00"
            }
        ],
        "requirements": [
            {
                "shiftTemplateId": "S_FRUEH",
                "date": start_date,
                "count": 1
            }
        ],
        "employees": [
            {
                "id": "E001",
                "name": "Max Mustermann",
                "contractHours": 40.0
            }
        ],
        "wishes": [
            {
                "employeeId": "E001",
                "date": start_date,
                "type": "OFF"
            }
        ]
    }
    
    result = validate_job_payload(payload)
    assert isinstance(result, JobPayload)
    assert result.metadata.jobId == "job-schema-1"
    assert result.metadata.tenantId == 1


def test_schema_accepts_legacy_payload_fields():
    """Test that legacy field names are accepted and normalized."""
    payload = {
        "metadata": {
            "tenantId": 1,
            "priority": 2,
            "timestamp": "2026-05-08T10:00:00Z"
        },
        "config": {
            "schemaVersion": "1.0",
            "startDate": "2026-01-01",
            "endDate": "2026-01-07"
        },
        "shiftTemplates": [
            {
                "id": "S_FRUEH",
                "name": "Frühschicht",
                "startTime": "06:00",
                "endTime": "14:00"
            }
        ],
        "requirements": [
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1}
            }
        ],
        "employees": [
            {
                "id": "E001",
                "name": "Max Mustermann",
                "contract": {
                    "weeklyHours": 40.0,
                    "employmentType": "Apotheker"
                },
                "skills": ["Apotheker"],
                "forbiddenDates": []
            }
        ],
        "wishes": [
            {
                "employeeId": "E001",
                "type": "PREFER_SHIFT",
                "shiftId": "S_FRUEH",
                "date": "2026-01-02",
                "weight": 2,
                "comment": "Frühschicht bevorzugt"
            }
        ]
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
    
    with pytest.raises(Exception):
        validate_job_payload(payload)


def test_schema_rejects_invalid_date_format():
    """Test that invalid date formats are rejected."""
    payload = {
        "metadata": {
            "jobId": "job-schema-3",
            "tenantId": 1
        },
        "config": {
            "schemaVersion": "1.0",
            "startDate": "invalid-date",
            "endDate": "2026-01-31"
        },
        "shiftTemplates": [],
        "requirements": [],
        "employees": []
    }
    
    with pytest.raises(Exception):
        validate_job_payload(payload)


def test_schema_rejects_invalid_time_format():
    """Test that invalid time formats are rejected."""
    payload = {
        "metadata": {
            "jobId": "job-schema-4",
            "tenantId": 1
        },
        "config": {
            "schemaVersion": "1.0",
            "startDate": "2026-01-01",
            "endDate": "2026-01-31"
        },
        "shiftTemplates": [
            {
                "id": "S_FRUEH",
                "name": "Frühschicht",
                "startTime": "invalid-time",
                "endTime": "14:00"
            }
        ],
        "requirements": [],
        "employees": []
    }
    
    with pytest.raises(Exception):
        validate_job_payload(payload)


def test_schema_rejects_unknown_fields():
    """Test that unknown fields are rejected."""
    payload = {
        "metadata": {
            "jobId": "job-schema-5",
            "tenantId": 1
        },
        "config": {
            "schemaVersion": "1.0",
            "startDate": "2026-01-01",
            "endDate": "2026-01-31"
        },
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
        "unknown_field": "should_be_rejected"
    }
    
    with pytest.raises(Exception):
        validate_job_payload(payload)


def test_schema_validates_date_range():
    """Test that startDate must be before endDate."""
    payload = {
        "metadata": {
            "jobId": "job-schema-6",
            "tenantId": 1
        },
        "config": {
            "schemaVersion": "1.0",
            "startDate": "2026-01-31",
            "endDate": "2026-01-01"
        },
        "shiftTemplates": [],
        "requirements": [],
        "employees": []
    }
    
    with pytest.raises(Exception):
        validate_job_payload(payload)


def test_schema_validates_references():
    """Test that references to non-existent shifts/employees are rejected."""
    payload = {
        "metadata": {
            "jobId": "job-schema-7",
            "tenantId": 1
        },
        "config": {
            "schemaVersion": "1.0",
            "startDate": "2026-01-01",
            "endDate": "2026-01-31"
        },
        "shiftTemplates": [],
        "requirements": [
            {
                "shiftTemplateId": "NON_EXISTENT",
                "date": "2026-01-01",
                "count": 1
            }
        ],
        "employees": []
    }
    
    with pytest.raises(Exception):
        validate_job_payload(payload)


def test_schema_with_minimal_required_fields():
    """Test that minimal valid payloads work."""
    payload = {
        "metadata": {
            "jobId": "job-schema-8",
            "tenantId": 1
        },
        "config": {
            "schemaVersion": "1.0",
            "startDate": "2026-01-01",
            "endDate": "2026-01-31"
        },
        "shiftTemplates": [],
        "requirements": [],
        "employees": []
    }
    
    result = validate_job_payload(payload)
    assert result.metadata.jobId == "job-schema-8"
    assert result.config.schemaVersion == "1.0"
