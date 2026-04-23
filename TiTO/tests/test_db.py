import json
from pathlib import Path

from tito.config import Settings
from tito.db import get_connection, enqueue_job, fetch_next_job, mark_job_processing, store_result


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

    mark_job_processing(connection, "job-test")
    result = {"status": "SUCCESS"}
    store_result(connection, "job-test", result)

    cursor = connection.execute("SELECT status, result FROM job_queue WHERE job_id = ?", ("job-test",))
    record = cursor.fetchone()
    assert record["status"] == "completed"
    assert json.loads(record["result"])["status"] == "SUCCESS"
