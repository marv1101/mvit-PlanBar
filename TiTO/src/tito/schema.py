import jsonschema

JOB_SCHEMA = {
    "type": "object",
    "required": ["metadata", "config", "shiftTemplates", "requirements", "employees"],
    "properties": {
        "metadata": {"type": "object"},
        "config": {"type": "object"},
        "shiftTemplates": {"type": "array"},
        "requirements": {"type": "array"},
        "employees": {"type": "array"},
        "wishes": {"type": ["array", "null"]},
    },
}


def validate_job_payload(payload: dict) -> None:
    """Validiert das JSON-Payload gegen das definierte Schema."""
    jsonschema.validate(payload, JOB_SCHEMA)
