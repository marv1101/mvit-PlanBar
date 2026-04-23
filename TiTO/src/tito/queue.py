from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    FAILED = "failed"
    COMPLETED = "completed"


def select_job(available_jobs: list[dict]) -> dict | None:
    """Wähle den nächsten Job aus der Queue aus."""
    return available_jobs[0] if available_jobs else None
