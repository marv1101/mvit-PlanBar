import pytest
from tito.schema import validate_job_payload


def test_schema_accepts_valid_payload():
    payload = {
        "metadata": {"jobId": "job-schema-1"},
        "config": {},
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
    }
    validate_job_payload(payload)


def test_schema_rejects_missing_required_fields():
    payload = {"metadata": {"jobId": "job-schema-2"}}
    with pytest.raises(Exception):
        validate_job_payload(payload)
