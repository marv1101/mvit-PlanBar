import time
from .config import Settings
from .db import get_connection, fetch_next_job, mark_job_processing, store_result
from .schema import validate_job_payload
from .solver import build_model, solve_model


def run_worker(settings: Settings) -> None:
    """Hauptschleife des TiTO-Workers."""
    connection = get_connection(settings.database_url)

    while True:
        job = fetch_next_job(connection, settings.queue_table)
        if job is None:
            time.sleep(1)
            continue

        try:
            mark_job_processing(connection, job["metadata"]["jobId"])
            validate_job_payload(job)
            model = build_model(job)
            result = solve_model(model, settings.timeout_seconds)
            store_result(connection, job["metadata"]["jobId"], result)
        except Exception as exc:
            print(f"Job failed: {exc}")
        time.sleep(0.1)
