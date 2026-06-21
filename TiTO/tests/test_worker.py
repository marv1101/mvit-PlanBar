"""
Tests für den TiTO Worker mit Fokus auf:
- Worker-Start/Stop
- Job-Verarbeitung
- Idempotenz-Prüfung
- Retry-Logik
- Callback-Verarbeitung
- Dead Letter Queue
- Heartbeat-Mechanismus
"""

import time
import uuid
from unittest.mock import Mock, patch
from datetime import datetime, timezone


from tito.config import Settings
from tito.worker import WorkerContext, run_worker, _process_pending_callbacks
from tito.db import (
    get_connection,
    enqueue_job,
    fetch_next_job,
    mark_job_processing,
    store_result,
    mark_job_failed_with_retry,
    move_job_to_dlq,
    enqueue_callback,
)


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
        settings, connection = setup_test_db(tmp_path)

        with patch("tito.worker.requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=200)
            with patch("tito.worker.psutil.cpu_percent", return_value=50.0):
                with patch("tito.worker.psutil.virtual_memory") as mock_vmem:
                    mock_vmem.return_value = Mock(percent=50.0)
                    with patch("tito.worker.fetch_next_job", return_value=None):
                        with patch("tito.worker._process_pending_callbacks"):
                            with self._setup_limited_worker(max_loops=1):
                                try:
                                    run_worker(settings)
                                except KeyboardInterrupt:
                                    pass

            # Prüfe, dass Register-Request gesendet wurde
            register_calls = [c for c in mock_post.call_args_list if "workers/register" in str(c)]
            assert len(register_calls) > 0

    def test_worker_sends_heartbeat(self, tmp_path):
        """Teste Heartbeat-Sendung."""
        settings, connection = setup_test_db(tmp_path)

        with patch("tito.worker.requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=200)
            with patch("tito.worker.psutil.cpu_percent", return_value=50.0):
                with patch("tito.worker.psutil.virtual_memory") as mock_vmem:
                    mock_vmem.return_value = Mock(percent=50.0)
                    with patch("tito.worker.fetch_next_job", return_value=None):
                        with patch("tito.worker._process_pending_callbacks"):
                            # Mock time.time() um Heartbeat zu erzwingen
                            current_time = [1000.0]  # Startwert

                            def mock_time():
                                return current_time[0]

                            def mock_sleep(duration):
                                current_time[0] += duration + 5  # Erhöhe Zeit um >5 Sekunden

                            with patch("tito.worker.time.time", side_effect=mock_time):
                                with patch("tito.worker.time.sleep", side_effect=mock_sleep):
                                    with self._setup_limited_worker(max_loops=3):
                                        try:
                                            run_worker(settings)
                                        except KeyboardInterrupt:
                                            pass

            # Prüfe, dass Heartbeat gesendet wurde
            heartbeat_calls = [c for c in mock_post.call_args_list if "workers/heartbeat" in str(c)]
            assert len(heartbeat_calls) > 0

    def test_worker_deregisters_on_shutdown(self, tmp_path):
        """Teste Deregistrierung beim Herunterfahren."""
        settings, connection = setup_test_db(tmp_path)

        with patch("tito.worker.requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=200)
            with patch("tito.worker.psutil.cpu_percent", return_value=50.0):
                with patch("tito.worker.psutil.virtual_memory") as mock_vmem:
                    mock_vmem.return_value = Mock(percent=50.0)
                    with patch("tito.worker.fetch_next_job", return_value=None):
                        with patch("tito.worker._process_pending_callbacks"):
                            with self._setup_limited_worker(max_loops=1):
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

        with patch("tito.worker.requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=200)
            with patch("tito.worker.psutil.cpu_percent", return_value=50.0):
                with patch("tito.worker.psutil.virtual_memory") as mock_vmem:
                    mock_vmem.return_value = Mock(percent=50.0)
                    with patch("tito.worker.build_model"):
                        with patch(
                            "tito.worker.solve_model",
                            return_value={"status": "SUCCESS"},
                        ):
                            with self._setup_limited_worker(max_loops=2):
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

        with patch("tito.worker.requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=200)
            with patch("tito.worker.psutil.cpu_percent", return_value=50.0):
                with patch("tito.worker.psutil.virtual_memory") as mock_vmem:
                    mock_vmem.return_value = Mock(percent=50.0)
                    with self._setup_limited_worker(max_loops=2):
                        try:
                            run_worker(settings)
                        except KeyboardInterrupt:
                            pass

        # Prüfe, dass Job als failed oder queued markiert wurde (retry)
        from tito.db import fetch_job_status_by_id

        job_status = fetch_job_status_by_id(connection, job_id)
        assert job_status is not None
        assert job_status["status"] in ["failed", "queued", "dead_lettered"]

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
            mock_post.side_effect = Exception("Network error")
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
