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
        "metadata": {"jobId": "job-test", "tenantId": 1, "priority": 1},
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


def test_idempotency_key_scoped_per_tenant(tmp_path: Path):
    """B6: Gleicher Idempotency-Key darf pro Tenant mehrfach existieren."""
    from tito.db import check_idempotency, enqueue_job, get_connection

    db_file = tmp_path / "test_idempotency_tenant.db"
    settings = Settings.from_env({"DATABASE_URL": f"sqlite:///{db_file}"})
    connection = get_connection(settings.database_url)

    payload_a = {"metadata": {"jobId": "job-a", "tenantId": 1}}
    payload_b = {"metadata": {"jobId": "job-b", "tenantId": 2}}

    job_a = enqueue_job(connection, payload_a, settings.queue_table, idempotency_key="sched_1", tenant_id="1")
    job_b = enqueue_job(connection, payload_b, settings.queue_table, idempotency_key="sched_1", tenant_id="2")

    assert job_a is not None
    assert job_b is not None
    assert job_a != job_b

    # Duplicate check ist mandanten-scoped
    dup_a = enqueue_job(connection, payload_a, settings.queue_table, idempotency_key="sched_1", tenant_id="1")
    assert dup_a is None  # Duplikat für Tenant 1

    # check_idempotency mit Tenant
    existing = check_idempotency(connection, "sched_1", tenant_id="1")
    assert existing is not None
    assert existing["job_id"] == job_a

    existing_b = check_idempotency(connection, "sched_1", tenant_id="2")
    assert existing_b is not None
    assert existing_b["job_id"] == job_b

    # Ohne Tenant findet er den ersten Treffer
    existing_any = check_idempotency(connection, "sched_1")
    assert existing_any is not None


def test_tenant_id_extracted_from_payload_fallback(tmp_path: Path):
    """B10: enqueue_job extrahiert tenant_id aus Payload-Metadata wenn nicht explizit übergeben."""
    from tito.db import enqueue_job, get_connection

    db_file = tmp_path / "test_tenant_fallback.db"
    settings = Settings.from_env({"DATABASE_URL": f"sqlite:///{db_file}"})
    connection = get_connection(settings.database_url)

    payload = {"metadata": {"jobId": "job-fb", "tenantId": 42}}
    job_id = enqueue_job(connection, payload, settings.queue_table)

    cursor = connection.execute("SELECT tenant_id FROM job_queue WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    assert row["tenant_id"] == "42"
