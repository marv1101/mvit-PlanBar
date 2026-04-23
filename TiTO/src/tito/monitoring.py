def record_job_metrics(job_id: str, duration_seconds: float, status: str) -> None:
    """Erfasse Metriken für den Joblauf."""
    pass


def get_metrics() -> dict:
    """Gibt aktuelle Monitoring-Daten zurück."""
    return {"queue_length": 0, "error_rate": 0.0}
