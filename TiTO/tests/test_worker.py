"""
Tests für den TiTO Worker mit Fokus auf:
- Worker-Start/Stop
- Job-Verarbeitung
- Idempotenz-Prüfung
- Retry-Logik
- Callback-Verarbeitung
- Dead Letter Queue
- Heartbeat-Mechanismus (F4: separater Thread)
- Atomares Job-Claiming (F1)
- Lease/Timeout-Recovery (F2)
- Fehler-Callbacks bei terminalem Fehlschlag (F3)
- Callback-Claiming/DLQ (F5)
- Callback-Auth via Authorization-Header (F7)
"""

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import requests
from tito.config import Settings
from tito.db import (
    enqueue_callback,
    enqueue_job,
    fetch_next_job,
    get_connection,
    mark_job_failed_with_retry,
    mark_job_processing,
    move_job_to_dlq,
    store_result,
)
from tito.worker import WorkerContext, _process_pending_callbacks, run_worker

# ============================================================================
# Helper-Funktionen für Tests
# ============================================================================


def create_test_payload(job_id: str = "test-job", priority: int = 0) -> dict:
    """Erstelle ein gültiges Test-Payload."""
    return {
        "metadata": {
            "jobId": job_id,
            "tenantId": 1,
            "priority": priority,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "config": {
            "startDate": "2026-05-13",
            "endDate": "2026-05-19",
            "maxDailyWorkHours": 10,
            "defaultWeeklyHours": 40,
        },
        "shiftTemplates": [
            {
                "id": "morning",
                "name": "Morning Shift",
                "startTime": "06:00",
                "endTime": "14:00",
                "color": "#FF6B6B",
            }
        ],
        "requirements": [{"shiftTemplateId": "morning", "date": "2026-05-13", "count": 1}],
        "employees": [
            {
                "id": "emp1",
                "name": "Max Mustermann",
                "contractHours": 40.0,
                "maxDailyHours": 10,
                "skills": ["basic"],
            }
        ],
    }


def setup_test_db(tmp_path, db_name: str = "test_worker.db") -> tuple[Settings, any]:
    """Einrichten einer Test-Datenbank."""
    db_file = tmp_path / db_name
    settings = Settings.from_env({"DATABASE_URL": f"sqlite:///{db_file}"})
    connection = get_connection(settings.database_url)
    return settings, connection


# ============================================================================
# Settings Tests (F2/F4/F7)
# ============================================================================


def test_settings_robustness_defaults_and_env_overrides():
    """F2/F4/F7: Neue Settings mit Defaults und Env-Overrides."""
    settings = Settings.from_env({})
    assert settings.job_lease_seconds == 600
    assert settings.heartbeat_interval_seconds == 15
    # Fallback: callback_api_key greift auf API_TOKEN, wenn TITO_CALLBACK_API_KEY
    # nicht gesetzt ist (Shared Secret zwischen TiTO und Backend).
    assert settings.callback_api_key == os.environ.get("API_TOKEN")

    settings = Settings.from_env(
        {
            "JOB_LEASE_SECONDS": "120",
            "HEARTBEAT_INTERVAL_SECONDS": "5",
            "TITO_CALLBACK_API_KEY": "cb-key",
        }
    )
    assert settings.job_lease_seconds == 120
    assert settings.heartbeat_interval_seconds == 5
    assert settings.callback_api_key == "cb-key"

    # Expliziter TITO_CALLBACK_API_KEY hat Vorrang vor API_TOKEN-Fallback.
    settings = Settings.from_env(
        {
            "TITO_CALLBACK_API_KEY": "explicit-cb-key",
            "API_TOKEN": "api-token",
        }
    )
    assert settings.callback_api_key == "explicit-cb-key"


# ============================================================================
# WorkerContext Tests
# ============================================================================


class TestWorkerContext:
    """Tests für WorkerContext-Klasse."""

    def test_initialization(self):
        """Teste Initialisierung des WorkerContext."""
        context = WorkerContext()
        assert context.should_stop is False
        assert context.current_job_id is None

    def test_request_stop(self):
        """Teste Stop-Anforderung durch Signal."""
        context = WorkerContext()
        context.request_stop()
        assert context.should_stop is True

    def test_request_stop_with_signum(self):
        """Teste Stop-Anforderung mit Signal-Nummer."""
        context = WorkerContext()
        context.request_stop(signum=15, frame=None)
        assert context.should_stop is True


# ============================================================================
# run_worker Tests (Unit-Tests mit Mocking)
# ============================================================================


class TestRunWorker:
    """Tests für die run_worker-Funktion."""

    def _setup_limited_worker(self, max_loops=1):
        """Setup für limitierte Worker-Durchläufe."""
        loop_counter = [0]
        original_sleep = time.sleep

        def mock_sleep(duration):
            """Mock sleep der Worker-Schleife - mit Loop-Limit."""
            loop_counter[0] += 1
            if loop_counter[0] >= max_loops:
                raise KeyboardInterrupt()  # Beende gracefully
            original_sleep(0.001)  # Kurzes echtes Sleep

        return patch("tito.worker.time.sleep", side_effect=mock_sleep)

    def test_worker_registers_at_startup(self, tmp_path):
        """Teste, dass Worker sich beim Start registriert."""
        settings, _connection = setup_test_db(tmp_path)

        with (
            patch("tito.worker.requests.post") as mock_post,
            patch("tito.worker.psutil.cpu_percent", return_value=50.0),
            patch("tito.worker.psutil.virtual_memory") as mock_vmem,
            patch("tito.worker.claim_next_job", return_value=None),
            patch("tito.worker._process_pending_callbacks"),
            self._setup_limited_worker(max_loops=1),
        ):
            mock_post.return_value = Mock(status_code=200)
            mock_vmem.return_value = Mock(percent=50.0)
            try:
                run_worker(settings)
            except KeyboardInterrupt:
                pass

            # Prüfe, dass Register-Request gesendet wurde
            register_calls = [c for c in mock_post.call_args_list if "workers/register" in str(c)]
            assert len(register_calls) > 0

    def test_worker_sends_heartbeat(self, tmp_path):
        """F4: Heartbeat läuft im separaten Daemon-Thread und pingt unabhängig vom Job-Loop."""
        settings, _connection = setup_test_db(tmp_path)
        settings.heartbeat_interval_seconds = 0.05

        loop_counter = [0]
        original_sleep = time.sleep

        def mock_sleep(duration):
            loop_counter[0] += 1
            if loop_counter[0] >= 2:
                raise KeyboardInterrupt()  # Beende gracefully
            original_sleep(0.2)  # gibt dem Heartbeat-Thread Zeit zu pingen

        with (
            patch("tito.worker.requests.post") as mock_post,
            patch("tito.worker.psutil.cpu_percent", return_value=50.0),
            patch("tito.worker.psutil.virtual_memory") as mock_vmem,
            patch("tito.worker.claim_next_job", return_value=None),
            patch("tito.worker._process_pending_callbacks"),
            patch("tito.worker.time.sleep", side_effect=mock_sleep),
        ):
            mock_post.return_value = Mock(status_code=200)
            mock_vmem.return_value = Mock(percent=50.0)
            try:
                run_worker(settings)
            except KeyboardInterrupt:
                pass

            # Prüfe, dass Heartbeat gesendet wurde
            heartbeat_calls = [c for c in mock_post.call_args_list if "workers/heartbeat" in str(c)]
            assert len(heartbeat_calls) > 0

    def test_worker_heartbeat_pings_during_blocking_solve(self, tmp_path):
        """F4: Während eines blockierenden Solves laufen die Heartbeats weiter (separater Thread)."""
        settings, connection = setup_test_db(tmp_path, "test_heartbeat_solve.db")
        settings.heartbeat_interval_seconds = 0.05

        payload = create_test_payload()
        payload["metadata"]["callback_url"] = "http://example.com/cb"
        job_id = enqueue_job(connection, payload, settings.queue_table)

        solve_started = threading.Event()
        release_solve = threading.Event()
        heartbeats: list[str] = []
        heartbeats_lock = threading.Lock()

        def fake_post(url, *args, **kwargs):
            if "workers/heartbeat" in str(url) and solve_started.is_set() and not release_solve.is_set():
                with heartbeats_lock:
                    heartbeats.append(str(url))
                if len(heartbeats) >= 3:
                    release_solve.set()
            return Mock(status_code=200)

        def fake_solve(model, timeout_seconds):
            solve_started.set()
            if not release_solve.wait(timeout=5):
                raise AssertionError("Heartbeat hat während des blockierenden Solves nicht gepingt")
            return {"metadata": {"status": "SUCCESS"}, "solution": {"assignments": []}}

        loop_counter = [0]
        original_sleep = time.sleep

        def mock_sleep(duration):
            loop_counter[0] += 1
            if loop_counter[0] >= 1:
                raise KeyboardInterrupt()
            original_sleep(0.001)

        with (
            patch("tito.worker.requests.post", side_effect=fake_post),
            patch("tito.worker.psutil.cpu_percent", return_value=50.0),
            patch("tito.worker.psutil.virtual_memory", return_value=Mock(percent=50.0)),
            patch("tito.worker.build_model"),
            patch("tito.worker.solve_model", side_effect=fake_solve),
            patch("tito.worker.time.sleep", side_effect=mock_sleep),
        ):
            try:
                run_worker(settings)
            except KeyboardInterrupt:
                pass

        # Heartbeats wurden während des blockierenden Solves gesendet
        assert len(heartbeats) >= 3

        from tito.db import fetch_job_status_by_id

        job_status = fetch_job_status_by_id(connection, job_id)
        assert job_status["status"] == "completed"

    def test_worker_deregisters_on_shutdown(self, tmp_path):
        """Teste Deregistrierung beim Herunterfahren."""
        settings, _connection = setup_test_db(tmp_path)

        with (
            patch("tito.worker.requests.post") as mock_post,
            patch("tito.worker.psutil.cpu_percent", return_value=50.0),
            patch("tito.worker.psutil.virtual_memory") as mock_vmem,
            patch("tito.worker.claim_next_job", return_value=None),
            patch("tito.worker._process_pending_callbacks"),
            self._setup_limited_worker(max_loops=1),
        ):
            mock_post.return_value = Mock(status_code=200)
            mock_vmem.return_value = Mock(percent=50.0)
            try:
                run_worker(settings)
            except KeyboardInterrupt:
                pass

            # Prüfe, dass Deregister-Request gesendet wurde
            deregister_calls = [c for c in mock_post.call_args_list if "workers/deregister" in str(c)]
            assert len(deregister_calls) > 0

    def test_worker_processes_job(self, tmp_path):
        """Teste Job-Verarbeitung."""
        settings, connection = setup_test_db(tmp_path)

        payload = create_test_payload()
        job_id = enqueue_job(connection, payload, settings.queue_table)

        with (
            patch("tito.worker.requests.post") as mock_post,
            patch("tito.worker.psutil.cpu_percent", return_value=50.0),
            patch("tito.worker.psutil.virtual_memory") as mock_vmem,
            patch("tito.worker.build_model"),
            patch(
                "tito.worker.solve_model",
                return_value={"status": "SUCCESS"},
            ),
            self._setup_limited_worker(max_loops=2),
        ):
            mock_post.return_value = Mock(status_code=200)
            mock_vmem.return_value = Mock(percent=50.0)
            try:
                run_worker(settings)
            except KeyboardInterrupt:
                pass

        # Prüfe, dass Job verarbeitet wurde
        from tito.db import fetch_job_status_by_id

        job_status = fetch_job_status_by_id(connection, job_id)
        assert job_status is not None
        assert job_status["status"] == "completed"

    def test_worker_handles_job_failure(self, tmp_path):
        """Teste Umgang mit Job-Fehlern."""
        settings, connection = setup_test_db(tmp_path)

        # Payload mit ungültigen Daten für Solver-Fehler
        payload = create_test_payload()
        payload["config"]["startDate"] = "invalid-date"  # Falsches Format

        job_id = enqueue_job(connection, payload, settings.queue_table)

        with (
            patch("tito.worker.requests.post") as mock_post,
            patch("tito.worker.psutil.cpu_percent", return_value=50.0),
            patch("tito.worker.psutil.virtual_memory") as mock_vmem,
            self._setup_limited_worker(max_loops=2),
        ):
            mock_post.return_value = Mock(status_code=200)
            mock_vmem.return_value = Mock(percent=50.0)
            try:
                run_worker(settings)
            except KeyboardInterrupt:
                pass

        # Prüfe, dass Job als failed oder queued markiert wurde (retry)
        from tito.db import fetch_job_status_by_id

        job_status = fetch_job_status_by_id(connection, job_id)
        assert job_status is not None
        assert job_status["status"] in ["failed", "queued", "dead_lettered"]

    def test_worker_stays_completed_when_callback_enqueue_fails(self, tmp_path):
        """Test that a job remains completed if callback enqueue fails after storing result."""
        settings, connection = setup_test_db(tmp_path, "test_callback_enqueue_failure.db")

        payload = create_test_payload()
        job_id = enqueue_job(connection, payload, settings.queue_table)

        with (
            patch("tito.worker.requests.post") as mock_post,
            patch("tito.worker.psutil.cpu_percent", return_value=50.0),
            patch("tito.worker.psutil.virtual_memory") as mock_vmem,
            patch("tito.worker.build_model"),
            patch(
                "tito.worker.solve_model",
                return_value={"status": "SUCCESS"},
            ),
            patch(
                "tito.worker.enqueue_callback",
                side_effect=RuntimeError("callback enqueue failed"),
            ),
            self._setup_limited_worker(max_loops=2),
        ):
            mock_post.return_value = Mock(status_code=200)
            mock_vmem.return_value = Mock(percent=50.0)
            try:
                run_worker(settings)
            except KeyboardInterrupt:
                pass

        from tito.db import fetch_job_status_by_id

        job_status = fetch_job_status_by_id(connection, job_id)
        assert job_status is not None
        assert job_status["status"] == "completed", (
            f"Job should stay completed even if callback enqueue fails, got {job_status['status']}"
        )

    def test_worker_handles_idempotency(self, tmp_path):
        """Teste Idempotenz-Prüfung."""
        settings, connection = setup_test_db(tmp_path)

        idempotency_key = str(uuid.uuid4())
        payload = create_test_payload()
        payload["metadata"]["idempotency_key"] = idempotency_key

        # Erster Job
        job_id1 = enqueue_job(connection, payload, settings.queue_table, idempotency_key=idempotency_key)

        # Zweiter Job mit gleicher Idempotenz-Key (sollte ignoriert werden)
        job_id2 = enqueue_job(connection, payload, settings.queue_table, idempotency_key=idempotency_key)

        assert job_id1 is not None
        assert job_id2 is None  # Doppelter wird abgelehnt

    def test_callbacks_and_reclaim_run_every_loop_iteration(self, tmp_path):
        """F5a/F2: Callbacks und Timeout-Recovery laufen in jedem Loop-Durchlauf - auch bei voller Queue."""
        settings, _connection = setup_test_db(tmp_path, "test_cb_every_loop.db")

        fake_job = create_test_payload()
        fake_job["_db_job_id"] = 999999  # existiert nicht in der DB -> DB-Updates sind No-Ops

        with (
            patch("tito.worker.requests.post", return_value=Mock(status_code=200)),
            patch("tito.worker.psutil.cpu_percent", return_value=50.0),
            patch("tito.worker.psutil.virtual_memory", return_value=Mock(percent=50.0)),
            patch("tito.worker.build_model"),
            patch("tito.worker.solve_model", return_value={"metadata": {"status": "SUCCESS"}}),
            patch("tito.worker.claim_next_job", side_effect=[fake_job, None]),
            patch("tito.worker._process_pending_callbacks") as mock_callbacks,
            patch("tito.worker.reclaim_timed_out_jobs") as mock_reclaim,
            self._setup_limited_worker(max_loops=2),
        ):
            try:
                run_worker(settings)
            except KeyboardInterrupt:
                pass

        # Callbacks werden NICHT nur bei leerer Queue bearbeitet (alte Starvation-Bug-Fix F5)
        assert mock_callbacks.call_count >= 2
        # Timeout-Sweep läuft in jeder Iteration (F2)
        assert mock_reclaim.call_count >= 2

    def test_worker_dlq_failure_enqueues_error_callback(self, tmp_path):
        """F3: Endgültiger Fehlschlag (DLQ) erzeugt Fehler-Callback mit error-Text und attempts."""
        settings, connection = setup_test_db(tmp_path, "test_dlq_callback.db")

        payload = create_test_payload()
        payload["metadata"]["callback_url"] = "http://example.com/cb"
        job_id = enqueue_job(connection, payload, settings.queue_table)

        # attempts bereits auf max_retries -> nächster Fehlschlag geht in die DLQ
        connection.execute("UPDATE job_queue SET attempts = 3 WHERE job_id = ?", (job_id,))
        connection.commit()

        sent_payloads: list[dict | None] = []

        def capture_post(url, *args, **kwargs):
            sent_payloads.append(kwargs.get("json"))
            return Mock(status_code=200)

        with (
            patch("tito.worker.requests.post", side_effect=capture_post),
            patch("tito.worker.psutil.cpu_percent", return_value=50.0),
            patch("tito.worker.psutil.virtual_memory", return_value=Mock(percent=50.0)),
            patch("tito.worker.build_model"),
            patch("tito.worker.solve_model", side_effect=RuntimeError("solver crashed")),
            self._setup_limited_worker(max_loops=2),
        ):
            try:
                run_worker(settings)
            except KeyboardInterrupt:
                pass

        from tito.db import fetch_job_status_by_id

        job_status = fetch_job_status_by_id(connection, job_id)
        assert job_status["status"] == "dead_lettered"

        # Fehler-Callback wurde enqueued und versendet
        error_callbacks = [p for p in sent_payloads if p and p.get("status") == "FAILED"]
        assert len(error_callbacks) == 1
        assert error_callbacks[0]["job_id"] == job_id
        assert "solver crashed" in error_callbacks[0]["error"]
        assert error_callbacks[0]["attempts"] >= 3

    def test_worker_infeasible_result_is_terminal_with_result_callback(self, tmp_path):
        """F3: INFEASIBLE ist terminal - Job wird completed gespeichert (KEIN Retry) + Ergebnis-Callback."""
        settings, connection = setup_test_db(tmp_path, "test_infeasible.db")

        payload = create_test_payload()
        payload["metadata"]["callback_url"] = "http://example.com/cb"
        job_id = enqueue_job(connection, payload, settings.queue_table)

        with (
            patch("tito.worker.requests.post", return_value=Mock(status_code=200)),
            patch("tito.worker.psutil.cpu_percent", return_value=50.0),
            patch("tito.worker.psutil.virtual_memory", return_value=Mock(percent=50.0)),
            patch("tito.worker.build_model"),
            patch(
                "tito.worker.solve_model",
                return_value={"metadata": {"status": "INFEASIBLE"}, "solution": {"assignments": []}},
            ),
            # Callbacks bleiben während des Runs pending, damit wir sie danach prüfen können
            patch("tito.worker._process_pending_callbacks"),
            self._setup_limited_worker(max_loops=2),
        ):
            try:
                run_worker(settings)
            except KeyboardInterrupt:
                pass

        from tito.db import fetch_job_status_by_id

        job_status = fetch_job_status_by_id(connection, job_id)
        assert job_status["status"] == "completed"  # terminal, KEIN Retry
        assert job_status["attempts"] == 1

        # Ergebnis-Callback wurde enqueued (Roh-Ergebnis inkl. INFEASIBLE-Status)
        row = connection.execute("SELECT result_payload FROM callback_queue WHERE job_id = ?", (job_id,)).fetchone()
        assert row is not None
        result_payload = json.loads(row["result_payload"])
        assert result_payload["metadata"]["status"] == "INFEASIBLE"


# ============================================================================
# _process_pending_callbacks Tests
# ============================================================================


class TestProcessPendingCallbacks:
    """Tests für die Callback-Verarbeitung."""

    def test_processes_callbacks_successfully(self, tmp_path):
        """Teste erfolgreichen Callback-Versand."""
        settings, connection = setup_test_db(tmp_path, "test_callbacks.db")

        # Callback in DB eintragen
        payload = create_test_payload()
        job_id = enqueue_job(connection, payload, settings.queue_table)
        enqueue_callback(
            connection,
            job_id,
            "http://example.com/callback",
            {"status": "success"},
            tenant_id="1",
        )

        with patch("tito.worker.requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=200)
            _process_pending_callbacks(connection, settings, {})

        # Prüfe, dass Callback als gesendet markiert wurde
        from tito.db import fetch_callback_status_by_job_id

        callback_status = fetch_callback_status_by_job_id(connection, job_id)
        assert len(callback_status) > 0
        assert callback_status[0]["callback_status"] == "sent"

    def test_callback_retry_on_failure(self, tmp_path):
        """Teste Callback-Retry bei HTTP-Fehler."""
        settings, connection = setup_test_db(tmp_path, "test_callback_retry.db")

        payload = create_test_payload()
        job_id = enqueue_job(connection, payload, settings.queue_table)
        enqueue_callback(
            connection,
            job_id,
            "http://example.com/callback",
            {"status": "success"},
            tenant_id="1",
        )

        with patch("tito.worker.requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=500)
            _process_pending_callbacks(connection, settings, {})

        # Prüfe, dass Callback als pending verbleibt (für Retry)
        from tito.db import fetch_callback_status_by_job_id

        callback_status = fetch_callback_status_by_job_id(connection, job_id)
        assert callback_status[0]["callback_status"] == "pending"

    def test_callback_retry_on_network_error(self, tmp_path):
        """Teste Callback-Retry bei Network-Fehler."""
        settings, connection = setup_test_db(tmp_path, "test_network_error.db")

        payload = create_test_payload()
        job_id = enqueue_job(connection, payload, settings.queue_table)
        enqueue_callback(
            connection,
            job_id,
            "http://example.com/callback",
            {"status": "success"},
            tenant_id="1",
        )

        with patch("tito.worker.requests.post") as mock_post:
            mock_post.side_effect = requests.RequestException("Network error")
            _process_pending_callbacks(connection, settings, {})

        # Prüfe, dass Callback als pending verbleibt
        from tito.db import fetch_callback_status_by_job_id

        callback_status = fetch_callback_status_by_job_id(connection, job_id)
        assert callback_status[0]["callback_status"] == "pending"

    def test_no_callbacks_to_process(self, tmp_path):
        """Teste ohne ausstehende Callbacks."""
        settings, connection = setup_test_db(tmp_path, "test_no_callbacks.db")

        # Sollte keine Exception werfen
        _process_pending_callbacks(connection, settings, {})

    def test_result_callback_sent_payload_format(self, tmp_path):
        """F3: Versandter Ergebnis-Callback enthält job_id + status (top-level ODER metadata.status)."""
        settings, connection = setup_test_db(tmp_path, "test_cb_format.db")

        payload = create_test_payload()
        job_id = enqueue_job(connection, payload, settings.queue_table)
        # Alt-Format: status in metadata
        enqueue_callback(
            connection,
            job_id,
            "http://example.com/cb",
            {"metadata": {"status": "INFEASIBLE"}, "solution": {"assignments": []}},
            tenant_id="1",
        )
        # Neu-Format: status top-level
        enqueue_callback(
            connection,
            job_id,
            "http://example.com/cb",
            {"status": "TIMEOUT", "solution": {"assignments": []}},
            tenant_id="1",
        )

        sent: list[dict | None] = []

        def capture_post(url, *args, **kwargs):
            sent.append(kwargs.get("json"))
            return Mock(status_code=200)

        with patch("tito.worker.requests.post", side_effect=capture_post):
            _process_pending_callbacks(connection, settings, {})

        assert len(sent) == 2
        by_status = {p["status"]: p for p in sent}
        assert by_status["INFEASIBLE"]["job_id"] == job_id
        assert "solution" in by_status["INFEASIBLE"]  # **result gemerged
        assert by_status["TIMEOUT"]["job_id"] == job_id
        assert by_status["TIMEOUT"]["status"] == "TIMEOUT"

    def test_callback_moves_to_failed_after_max_attempts(self, tmp_path):
        """F5c: Nach 3 fehlgeschlagenen Versuchen landet der Callback im Status 'failed' (Callback-DLQ)."""
        settings, connection = setup_test_db(tmp_path, "test_cb_failed.db")

        payload = create_test_payload()
        job_id = enqueue_job(connection, payload, settings.queue_table)
        enqueue_callback(
            connection,
            job_id,
            "http://example.com/callback",
            {"metadata": {"status": "SUCCESS"}},
            tenant_id="1",
        )

        with patch("tito.worker.requests.post", return_value=Mock(status_code=500)):
            _process_pending_callbacks(connection, settings, {})
            _process_pending_callbacks(connection, settings, {})
            _process_pending_callbacks(connection, settings, {})

        from tito.db import fetch_callback_status_by_job_id

        callback_status = fetch_callback_status_by_job_id(connection, job_id)
        assert callback_status[0]["callback_status"] == "failed"
        assert callback_status[0]["attempts"] == 3

    def test_callback_sent_exactly_once_on_success(self, tmp_path):
        """F5b: Claiming verhindert Doppelversand - erfolgreicher Callback wird nur 1x gesendet."""
        settings, connection = setup_test_db(tmp_path, "test_cb_once.db")

        payload = create_test_payload()
        job_id = enqueue_job(connection, payload, settings.queue_table)
        enqueue_callback(
            connection,
            job_id,
            "http://example.com/callback",
            {"metadata": {"status": "SUCCESS"}},
            tenant_id="1",
        )

        with patch("tito.worker.requests.post", return_value=Mock(status_code=200)) as mock_post:
            _process_pending_callbacks(connection, settings, {})
            _process_pending_callbacks(connection, settings, {})

        assert mock_post.call_count == 1

        from tito.db import fetch_callback_status_by_job_id

        callback_status = fetch_callback_status_by_job_id(connection, job_id)
        assert callback_status[0]["callback_status"] == "sent"
        assert callback_status[0]["attempts"] == 1

    def test_callback_send_uses_bearer_authorization_header(self, tmp_path):
        """F7: Mit gesetztem callback_api_key wird ein Authorization-Header gesendet."""
        settings, connection = setup_test_db(tmp_path, "test_cb_auth.db")
        settings.callback_api_key = "secret-callback-key"

        payload = create_test_payload()
        job_id = enqueue_job(connection, payload, settings.queue_table)
        enqueue_callback(
            connection,
            job_id,
            "http://example.com/callback",
            {"metadata": {"status": "SUCCESS"}},
            tenant_id="1",
        )

        with patch("tito.worker.requests.post", return_value=Mock(status_code=200)) as mock_post:
            _process_pending_callbacks(connection, settings, {})

        headers = mock_post.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer secret-callback-key"

    def test_callback_send_without_key_omits_authorization_header(self, tmp_path):
        """F7: Ohne callback_api_key wird kein Authorization-Header gesendet (nur Development)."""
        settings, connection = setup_test_db(tmp_path, "test_cb_noauth.db")
        settings.callback_api_key = None

        payload = create_test_payload()
        job_id = enqueue_job(connection, payload, settings.queue_table)
        enqueue_callback(
            connection,
            job_id,
            "http://example.com/callback",
            {"metadata": {"status": "SUCCESS"}},
            tenant_id="1",
        )

        with patch("tito.worker.requests.post", return_value=Mock(status_code=200)) as mock_post:
            _process_pending_callbacks(connection, settings, {})

        headers = mock_post.call_args.kwargs["headers"]
        assert "Authorization" not in headers


# ============================================================================
# Integration Tests (mit echter Datenbank)
# ============================================================================


class TestWorkerIntegration:
    """Integrationstests für Worker mit echter DB."""

    def test_full_job_lifecycle(self, tmp_path):
        """Teste kompletten Job-Lebenszyklus."""
        settings, connection = setup_test_db(tmp_path, "test_full_lifecycle.db")

        payload = create_test_payload()
        job_id = enqueue_job(connection, payload, settings.queue_table)

        # Job abrufen
        job = fetch_next_job(connection, settings.queue_table)
        assert job is not None
        assert job["_db_job_id"] == job_id

        # Job als processing markieren
        mark_job_processing(connection, job_id)

        # Ergebnis speichern
        result = {"assignments": [], "status": "SUCCESS"}
        store_result(connection, job_id, result)

        # Prüfe, dass Job als completed markiert ist
        from tito.db import fetch_job_status_by_id

        job_status = fetch_job_status_by_id(connection, job_id)
        assert job_status["status"] == "completed"
        assert job_status["result"]["status"] == "SUCCESS"

    def test_job_retry_lifecycle(self, tmp_path):
        """Teste Job-Retry mit exponential backoff."""
        settings, connection = setup_test_db(tmp_path, "test_retry.db")

        payload = create_test_payload()
        job_id = enqueue_job(connection, payload, settings.queue_table)

        # Job als failed markieren (erster Versuch)
        # Zuerst attempts counter erhöhen
        connection.execute("UPDATE job_queue SET attempts = attempts + 1 WHERE job_id = ?", (job_id,))
        connection.commit()

        mark_job_failed_with_retry(connection, job_id, "Test error 1")

        from tito.db import fetch_job_status_by_id

        job_status = fetch_job_status_by_id(connection, job_id)
        assert job_status["status"] == "queued"  # Wird retryt
        assert job_status["attempts"] == 1

        # Nochmal failed (zweiter Versuch)
        connection.execute("UPDATE job_queue SET attempts = attempts + 1 WHERE job_id = ?", (job_id,))
        connection.commit()
        mark_job_failed_with_retry(connection, job_id, "Test error 2")
        job_status = fetch_job_status_by_id(connection, job_id)
        assert job_status["attempts"] == 2

        # Dritter Versuch - sollte in DLQ landen
        connection.execute("UPDATE job_queue SET attempts = attempts + 1 WHERE job_id = ?", (job_id,))
        connection.commit()
        mark_job_failed_with_retry(connection, job_id, "Test error 3")
        job_status = fetch_job_status_by_id(connection, job_id)
        assert job_status["status"] == "failed"  # Max retries überschritten

    def test_dlq_migration(self, tmp_path):
        """Teste Migration zur Dead Letter Queue."""
        settings, connection = setup_test_db(tmp_path, "test_dlq.db")

        payload = create_test_payload()
        job_id = enqueue_job(connection, payload, settings.queue_table)

        # Job zur DLQ hinzufügen
        dlq_id = move_job_to_dlq(
            connection,
            job_id,
            payload,
            "Max retries exceeded",
            attempts=3,
            tenant_id="1",
        )

        assert dlq_id is not None

        # Prüfe DLQ-Eintrag
        from tito.db import fetch_dlq_jobs

        dlq_jobs = fetch_dlq_jobs(connection)
        assert len(dlq_jobs) == 1
        assert dlq_jobs[0]["failure_reason"] == "Max retries exceeded"

        # Prüfe, dass Job in Queue als dead_lettered markiert ist
        from tito.db import fetch_job_status_by_id

        job_status = fetch_job_status_by_id(connection, job_id)
        assert job_status["status"] == "dead_lettered"

    def test_worker_uses_validated_tenantId_for_callback_and_dlq(self, tmp_path):
        """B2: Worker extrahiert tenant_id aus dem Payload (camelCase tenantId) für Callback + DLQ."""
        from tito.db import enqueue_callback, fetch_callback_status_by_job_id

        settings, connection = setup_test_db(tmp_path, "test_tenant_extract.db")

        # Payload mit camelCase tenantId (wie im README dokumentiert), KEIN snake_case tenant_id
        payload = create_test_payload(job_id="job-camel")
        payload["metadata"]["callback_url"] = "http://example.com/cb"
        # Entferne ggf. snake_case, falls vom Test-Helper gesetzt
        payload["metadata"].pop("tenant_id", None)

        job_id = enqueue_job(connection, payload, settings.queue_table)

        # Simuliere Worker-Callback-Eintrag via extract_tenant_id (wie worker.py es tut)
        from tito.schema import extract_tenant_id

        tenant_id = extract_tenant_id(payload.get("metadata"))
        assert tenant_id == "1"  # aus tenantId (int) -> str normalisiert

        enqueue_callback(connection, job_id, "http://example.com/cb", {"status": "ok"}, tenant_id=tenant_id)

        callbacks = fetch_callback_status_by_job_id(connection, job_id, tenant_id="1")
        assert len(callbacks) == 1

        # Cross-Tenant: Tenant 2 sieht den Callback nicht
        callbacks_b = fetch_callback_status_by_job_id(connection, job_id, tenant_id="2")
        assert len(callbacks_b) == 0
