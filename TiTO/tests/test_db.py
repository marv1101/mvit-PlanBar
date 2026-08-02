import json
from pathlib import Path

from tito.config import Settings
from tito.db import (
    enqueue_job,
    fetch_next_job,
    get_connection,
    mark_job_processing,
    store_result,
)


def test_sqlite_job_lifecycle(tmp_path: Path):
    db_file = tmp_path / "test_tito.db"
    settings = Settings.from_env({"DATABASE_URL": f"sqlite:///{db_file}"})
    connection = get_connection(settings.database_url)

    payload = {
        "metadata": {"jobId": "job-test", "priority": 1},
        "config": {},
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
    }

    enqueue_job(connection, payload, settings.queue_table)
    job = fetch_next_job(connection, settings.queue_table)

    assert job is not None
    assert job["metadata"]["jobId"] == "job-test"

    db_job_id = job.pop("_db_job_id")  # Extract the database job ID
    mark_job_processing(connection, db_job_id)
    result = {"status": "SUCCESS"}
    store_result(connection, db_job_id, result)

    cursor = connection.execute("SELECT status, result FROM job_queue WHERE job_id = ?", (db_job_id,))
    record = cursor.fetchone()
    assert record["status"] == "completed"
    assert json.loads(record["result"])["status"] == "SUCCESS"
