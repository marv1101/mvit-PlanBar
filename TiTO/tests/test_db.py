import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tito.config import Settings
from tito.db import (
    claim_callback,
    claim_next_job,
    enqueue_callback,
    enqueue_job,
    fetch_callback_status_by_job_id,
    fetch_dlq_jobs,
    fetch_next_job,
    fetch_pending_callbacks,
    get_connection,
    mark_job_processing,
    reclaim_timed_out_jobs,
    requeue_stale_sending_callbacks,
    retry_job,
    store_callback_result,
    store_result,
)


def _make_settings_and_connection(tmp_path: Path, name: str) -> tuple[Settings, object]:
    db_file = tmp_path / name
    settings = Settings.from_env({"DATABASE_URL": f"sqlite:///{db_file}"})
    return settings, get_connection(settings.database_url)


def _enqueue_simple_job(connection, queue_table: str, job_id: str = "job-x", callback_url: str | None = None) -> int:
    payload = {
        "metadata": {"jobId": job_id, "tenantId": 1, "priority": 0},
        "config": {},
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
    }
    return enqueue_job(connection, payload, queue_table, callback_url=callback_url, tenant_id="1")


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


# ============================================================================
# F1/F8: Atomares Job-Claiming (Race Condition)
# ============================================================================


def test_mark_job_processing_is_guarded_claim_with_lease(tmp_path: Path):
    """F1/F2: mark_job_processing claimed nur 'queued'-Jobs, inkrementiert attempts genau einmal und setzt timeout_at."""
    settings, connection = _make_settings_and_connection(tmp_path, "claim_guard.db")
    job_id = _enqueue_simple_job(connection, settings.queue_table)

    before = datetime.now(timezone.utc)
    assert mark_job_processing(connection, job_id, lease_seconds=600) is True

    row = connection.execute(
        "SELECT status, attempts, timeout_at FROM job_queue WHERE job_id = ?", (job_id,)
    ).fetchone()
    assert row["status"] == "processing"
    assert row["attempts"] == 1
    timeout_at = datetime.fromisoformat(row["timeout_at"])
    assert before + timedelta(seconds=590) <= timeout_at <= before + timedelta(seconds=610)

    # Zweiter Claim auf denselben Job schlägt fehl (Race-Schutz) und verändert nichts
    assert mark_job_processing(connection, job_id, lease_seconds=600) is False
    row = connection.execute("SELECT attempts, status FROM job_queue WHERE job_id = ?", (job_id,)).fetchone()
    assert row["attempts"] == 1
    assert row["status"] == "processing"


def test_claim_next_job_no_double_claim_two_connections(tmp_path: Path):
    """F1/F8: Zwei konkurrente Claimer (separate Verbindungen) erhalten nie denselben Job."""
    settings, setup_conn = _make_settings_and_connection(tmp_path, "claim_race.db")
    expected_ids = {_enqueue_simple_job(setup_conn, settings.queue_table, f"job-{i}") for i in range(5)}

    claimer_conns = [get_connection(settings.database_url) for _ in range(2)]
    claimed: list[int] = []
    claimed_lock = threading.Lock()

    def claimer(conn):
        local = []
        while True:
            job = claim_next_job(conn, settings.queue_table, lease_seconds=600)
            if job is None:
                break
            local.append(job["_db_job_id"])
        with claimed_lock:
            claimed.extend(local)

    threads = [threading.Thread(target=claimer, args=(conn,)) for conn in claimer_conns]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert not any(thread.is_alive() for thread in threads), "Claimer-Threads haben sich aufgehängt"
    assert len(claimed) == 5
    assert len(set(claimed)) == 5, "Ein Job wurde doppelt geclaimt"
    assert set(claimed) == expected_ids

    for job_id in expected_ids:
        row = setup_conn.execute("SELECT attempts FROM job_queue WHERE job_id = ?", (job_id,)).fetchone()
        assert row["attempts"] == 1


# ============================================================================
# F2: Lease/Timeout - Festhängende 'processing'-Jobs
# ============================================================================


def test_reclaim_timed_out_jobs_requeues_stuck_job(tmp_path: Path):
    """F2: 'processing'-Job mit abgelaufenem timeout_at wird zurück auf 'queued' gesetzt."""
    settings, connection = _make_settings_and_connection(tmp_path, "reclaim_requeue.db")
    job_id = _enqueue_simple_job(connection, settings.queue_table)
    mark_job_processing(connection, job_id, lease_seconds=600)

    # Lease in die Vergangenheit manipulieren (simulierter Worker-Crash)
    stale = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    connection.execute("UPDATE job_queue SET timeout_at = ? WHERE job_id = ?", (stale, job_id))
    connection.commit()

    reclaimed = reclaim_timed_out_jobs(connection, settings.queue_table)
    assert [entry["job_id"] for entry in reclaimed] == [job_id]
    assert reclaimed[0]["action"] == "requeued"

    row = connection.execute(
        "SELECT status, timeout_at, last_error FROM job_queue WHERE job_id = ?", (job_id,)
    ).fetchone()
    assert row["status"] == "queued"
    assert row["timeout_at"] is None
    assert row["last_error"] is not None

    # Der Job ist danach wieder holbar
    job = fetch_next_job(connection, settings.queue_table)
    assert job is not None
    assert job["_db_job_id"] == job_id


def test_reclaim_timed_out_jobs_exhausted_moves_to_dlq_with_error_callback(tmp_path: Path):
    """F2/F3: Erschöpfte Versuche + abgelaufener Lease -> DLQ + Fehler-Callback."""
    settings, connection = _make_settings_and_connection(tmp_path, "reclaim_dlq.db")
    job_id = _enqueue_simple_job(connection, settings.queue_table, callback_url="http://example.com/cb")

    stale = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    connection.execute(
        "UPDATE job_queue SET status = 'processing', attempts = 3, timeout_at = ? WHERE job_id = ?",
        (stale, job_id),
    )
    connection.commit()

    reclaimed = reclaim_timed_out_jobs(connection, settings.queue_table)
    assert reclaimed[0]["action"] == "dead_lettered"

    row = connection.execute("SELECT status FROM job_queue WHERE job_id = ?", (job_id,)).fetchone()
    assert row["status"] == "dead_lettered"
    assert len(fetch_dlq_jobs(connection)) == 1

    # F3: Fehler-Callback mit FAILED-Payload wurde enqueued
    callbacks = fetch_callback_status_by_job_id(connection, job_id)
    assert len(callbacks) == 1
    payload_row = connection.execute(
        "SELECT result_payload, callback_status FROM callback_queue WHERE job_id = ?", (job_id,)
    ).fetchone()
    payload = json.loads(payload_row["result_payload"])
    assert payload["job_id"] == job_id
    assert payload["status"] == "FAILED"
    assert payload["attempts"] == 3
    assert payload["error"]


# ============================================================================
# F6: Manual-Retry mit attempts-Reset
# ============================================================================


def test_retry_job_resets_attempts_and_errors(tmp_path: Path):
    """F6: retry_job setzt attempts, last_error und timeout_at zurück."""
    settings, connection = _make_settings_and_connection(tmp_path, "retry_reset.db")
    job_id = _enqueue_simple_job(connection, settings.queue_table)

    connection.execute(
        "UPDATE job_queue SET status = 'failed', attempts = 3, last_error = 'boom', "
        "timeout_at = '2026-01-01T00:00:00+00:00', scheduled_for = '2030-01-01T00:00:00+00:00' "
        "WHERE job_id = ?",
        (job_id,),
    )
    connection.commit()

    assert retry_job(connection, job_id) is True
    row = connection.execute(
        "SELECT status, attempts, last_error, timeout_at, scheduled_for FROM job_queue WHERE job_id = ?",
        (job_id,),
    ).fetchone()
    assert row["status"] == "queued"
    assert row["attempts"] == 0
    assert row["last_error"] is None
    assert row["timeout_at"] is None
    assert row["scheduled_for"] is None

    # Ein Job, der nicht 'failed'/'dead_lettered' ist, kann nicht retried werden
    assert retry_job(connection, job_id) is False


# ============================================================================
# F5: Atomares Callback-Claiming
# ============================================================================


def test_claim_callback_is_atomic(tmp_path: Path):
    """F5: Claim VOR Versand verhindert Doppelversand; attempts wird nur beim Claim inkrementiert."""
    settings, connection = _make_settings_and_connection(tmp_path, "cb_claim.db")
    job_id = _enqueue_simple_job(connection, settings.queue_table)
    enqueue_callback(connection, job_id, "http://example.com/cb", {"metadata": {"status": "SUCCESS"}}, tenant_id="1")

    callbacks = fetch_pending_callbacks(connection)
    callback_id = callbacks[0]["callback_id"]
    assert callbacks[0]["attempts"] == 0

    assert claim_callback(connection, callback_id) is True
    row = connection.execute(
        "SELECT callback_status, attempts FROM callback_queue WHERE callback_id = ?", (callback_id,)
    ).fetchone()
    assert row["callback_status"] == "sending"
    assert row["attempts"] == 1

    # Zweiter Worker kann denselben Callback nicht erneut claimen
    assert claim_callback(connection, callback_id) is False
    row = connection.execute(
        "SELECT callback_status, attempts FROM callback_queue WHERE callback_id = ?", (callback_id,)
    ).fetchone()
    assert row["callback_status"] == "sending"
    assert row["attempts"] == 1

    # store_callback_result erhöht attempts NICHT nochmals (Claim hat bereits inkrementiert)
    store_callback_result(connection, callback_id, "sent")
    row = connection.execute(
        "SELECT callback_status, attempts FROM callback_queue WHERE callback_id = ?", (callback_id,)
    ).fetchone()
    assert row["callback_status"] == "sent"
    assert row["attempts"] == 1


def test_requeue_stale_sending_callbacks(tmp_path: Path):
    """F5: Im Status 'sending' hängengebliebene Callbacks (Worker-Crash) werden re-queued."""
    settings, connection = _make_settings_and_connection(tmp_path, "cb_stale.db")
    job_id = _enqueue_simple_job(connection, settings.queue_table)
    enqueue_callback(connection, job_id, "http://example.com/cb", {"status": "ok"}, tenant_id="1")
    enqueue_callback(connection, job_id, "http://example.com/cb2", {"status": "ok"}, tenant_id="1")

    callbacks = fetch_pending_callbacks(connection)
    stale_id = callbacks[0]["callback_id"]
    fresh_id = callbacks[1]["callback_id"]
    assert claim_callback(connection, stale_id) is True
    assert claim_callback(connection, fresh_id) is True

    # Stale: attempted_at in die Vergangenheit verschieben
    stale_time = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    connection.execute("UPDATE callback_queue SET attempted_at = ? WHERE callback_id = ?", (stale_time, stale_id))
    connection.commit()

    assert requeue_stale_sending_callbacks(connection, stale_seconds=60) == 1

    statuses = {c["callback_id"]: c["callback_status"] for c in fetch_callback_status_by_job_id(connection, job_id)}
    assert statuses[stale_id] == "pending"
    assert statuses[fresh_id] == "sending"
