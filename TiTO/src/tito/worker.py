import json as json_module
import logging
import signal
import threading
import time
import uuid
from typing import Any

import psutil
import requests

from .config import Settings
from .db import (
    claim_callback,
    claim_next_job,
    enqueue_callback,
    fetch_job_status_by_id,
    fetch_pending_callbacks,
    get_connection,
    mark_job_failed_with_retry,
    move_job_to_dlq,
    reclaim_timed_out_jobs,
    requeue_stale_sending_callbacks,
    store_callback_result,
    store_result,
)
from .schema import JobPayload, extract_tenant_id, validate_job_payload
from .solver import build_model, solve_model


class WorkerContext:
    """Context for managing worker lifecycle and job processing state."""

    def __init__(self):
        self.should_stop = False
        self.current_job_id: int | None = None

    def request_stop(self, signum=None, frame=None):
        """Signal handler for graceful shutdown."""
        logger = logging.getLogger(__name__)
        logger.info("Received shutdown signal. Finishing current job...")
        self.should_stop = True


def _extract_result_status(result_payload: dict) -> str:
    """F3: Status eines Solver-Ergebnisses extrahieren.

    Unterstützt beide Formate: top-level 'status' (neu) und metadata.status (bestehend)."""
    status = result_payload.get("status")
    if isinstance(status, str) and status:
        return status
    metadata = result_payload.get("metadata")
    if isinstance(metadata, dict):
        status = metadata.get("status")
        if isinstance(status, str) and status:
            return status
    return "unknown"


def _heartbeat_loop(
    stop_event: threading.Event,
    settings: Settings,
    worker_id: str,
    headers: dict,
    state: dict,
) -> None:
    """F4: Heartbeat in separatem Daemon-Thread.

    Läuft unabhängig vom Job-Loop, sodass Heartbeats auch während eines blockierenden
    solve_model (bis zu settings.timeout_seconds) weitergesendet werden und der Worker
    nicht fälschlich aus der Registry entfernt wird. Shutdown sauber via threading.Event."""
    logger = logging.getLogger(__name__)
    while not stop_event.is_set():
        try:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            requests.post(
                f"{settings.api_url}/workers/heartbeat",
                json={
                    "worker_id": worker_id,
                    "cpu_usage": cpu,
                    "ram_usage": ram,
                    "active_jobs": state.get("active_jobs", 0),
                },
                timeout=5,
                headers=headers,
            )
        except requests.RequestException as e:
            logger.error(f"Failed to send heartbeat: {e}")
        stop_event.wait(settings.heartbeat_interval_seconds)


def _enqueue_result_callback(
    connection: Any,
    db_job_id: int,
    callback_url: str,
    result: dict,
    job: dict,
    logger: logging.Logger,
) -> None:
    """F3: Ergebnis-Callback enqueueen (Erfolgsfall und terminale Solver-Status)."""
    try:
        enqueue_callback(
            connection,
            db_job_id,
            callback_url,
            result,
            tenant_id=extract_tenant_id(job.get("metadata")),
        )
        logger.info(f"Job {db_job_id}: Callback enqueued")
    except Exception:
        # The solver result is already stored. A failing callback enqueue must not fail
        # the whole job; the callback queue retry mechanism handles delivery separately.
        logger.exception(f"Job {db_job_id}: Result stored but callback enqueue failed")


def _enqueue_error_callback(
    connection: Any,
    db_job_id: int,
    callback_url: str | None,
    error: str,
    attempts: int,
    job: dict,
    logger: logging.Logger,
) -> None:
    """F3: Fehler-Callback bei terminalem Fehlschlag (DLQ) enqueueen."""
    if not callback_url:
        return
    try:
        enqueue_callback(
            connection,
            db_job_id,
            callback_url,
            {"job_id": db_job_id, "status": "FAILED", "error": error, "attempts": attempts},
            tenant_id=extract_tenant_id(job.get("metadata")),
        )
        logger.info(f"Job {db_job_id}: Error callback enqueued")
    except Exception:
        logger.exception(f"Job {db_job_id}: Failed to enqueue error callback")


def run_worker(settings: Settings) -> None:
    """Hauptschleife des TiTO-Workers mit Robustness-Features."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    logger.info("Starting TiTO Worker...")
    worker_id = str(uuid.uuid4())
    logger.info(f"Worker ID: {worker_id}")

    # Setup graceful shutdown
    worker_context = WorkerContext()
    try:
        signal.signal(signal.SIGTERM, worker_context.request_stop)
        signal.signal(signal.SIGINT, worker_context.request_stop)
    except ValueError:
        # signal() ist nur im Main-Thread erlaubt (z.B. Embedded-/Test-Betrieb);
        # Shutdown erfolgt dann weiterhin über Exceptions bzw. den Loop-Exit.
        logger.warning("Signal handlers not available outside the main thread")

    # Sammle initiale Stats
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent

    # B9: Dediziertes Worker-Token bevorzugen (Rolle 'worker'), Fallback auf API-Tokens.
    worker_token = settings.worker_api_token or (settings.api_tokens[0] if settings.api_tokens else None)

    # Registriere bei der API
    headers = {}
    if worker_token:
        headers["Authorization"] = f"Bearer {worker_token}"

    try:
        requests.post(
            f"{settings.api_url}/workers/register",
            json={"worker_id": worker_id, "cpu_usage": cpu, "ram_usage": ram},
            timeout=5,
            headers=headers,
        )
    except requests.RequestException as e:
        logger.error(f"Failed to register worker: {e}")

    connection = get_connection(settings.database_url)

    # F4: Heartbeat im separaten Daemon-Thread (läuft während solve_model weiter)
    heartbeat_stop = threading.Event()
    heartbeat_state: dict = {"active_jobs": 0}
    heartbeat_thread = threading.Thread(
        target=_heartbeat_loop,
        args=(heartbeat_stop, settings, worker_id, headers, heartbeat_state),
        daemon=True,
        name=f"tito-heartbeat-{worker_id[:8]}",
    )
    heartbeat_thread.start()

    try:
        while not worker_context.should_stop:
            try:
                # F5a: Pending-Callbacks in JEDEM Loop-Durchlauf bearbeiten
                # (kein Verzug mehr, wenn die Job-Queue voll ist)
                _process_pending_callbacks(connection, settings, headers)

                # F2: Festhängende Jobs (abgelaufener Lease) re-queued oder terminal abschließen
                reclaimed = reclaim_timed_out_jobs(connection, settings.queue_table)
                for entry in reclaimed:
                    logger.warning(
                        f"Reclaimed stuck job {entry['job_id']} ({entry['action']}) after lease timeout"
                    )

                # F1: Atomaren Claim des nächsten fälligen Jobs
                job = claim_next_job(connection, settings.queue_table, settings.job_lease_seconds)
                if job is None:
                    time.sleep(1)
                    continue

                db_job_id = job.pop("_db_job_id")
                worker_context.current_job_id = db_job_id
                heartbeat_state["active_jobs"] = heartbeat_state.get("active_jobs", 0) + 1

                result_stored = False
                try:
                    logger.info(f"Processing job ID: {db_job_id}")

                    # Validate payload and get Pydantic model
                    job_payload: JobPayload = validate_job_payload(job)

                    # Build and solve model (with timeout)
                    model = build_model(job_payload.model_dump())
                    # D5: Konfigurierter Payload-Timeout (solverTimeoutSeconds) wird
                    # respektiert, aber an die Worker-Hard-Cap gekürzt - der Tenant
                    # kann den Timeout nicht beliebig erhöhen.
                    configured_timeout = (model.get("config") or {}).get("solverTimeoutSeconds")
                    if configured_timeout:
                        solve_timeout = min(int(configured_timeout), settings.timeout_seconds)
                    else:
                        solve_timeout = settings.timeout_seconds
                    result = solve_model(model, solve_timeout)

                    # Terminal: SUCCESS/FEASIBLE/INFEASIBLE/TIMEOUT sind Ergebnisse, KEINE Fehler -
                    # der Job wird completed gespeichert und per Ergebnis-Callback gemeldet (F3).
                    # Nur Exceptions (z.B. invalid input) gehen in das Retry-Handling.
                    store_result(connection, db_job_id, result)
                    result_stored = True
                    logger.info(f"Job {db_job_id}: Completed with status {_extract_result_status(result)}")

                    # enqueue result callback if requested
                    callback_url = job.get("metadata", {}).get("callback_url")
                    if callback_url:
                        _enqueue_result_callback(connection, db_job_id, callback_url, result, job, logger)

                    # F5a: Callbacks mit niedriger Latenz auch direkt nach Job-Abschluss versenden
                    _process_pending_callbacks(connection, settings, headers)

                except Exception as exc:
                    if result_stored:
                        # Something went wrong after the result was already persisted.
                        # Do NOT retry the job; log the post-completion error with details.
                        logger.exception(
                            f"Job {db_job_id}: Post-completion error after result was stored",
                        )
                    else:
                        logger.exception(f"Job {db_job_id} failed")

                        # try to retry with exponential backoff
                        will_retry = mark_job_failed_with_retry(
                            connection, db_job_id, str(exc), settings.retry_base_delay
                        )

                        if not will_retry:
                            # Max retries exceeded, move to DLQ
                            job_status = fetch_job_status_by_id(connection, db_job_id)
                            attempts = (job_status or {}).get("attempts") or 0
                            move_job_to_dlq(
                                connection,
                                db_job_id,
                                job,
                                f"Max retries exceeded: {exc}",
                                attempts=attempts,
                                tenant_id=extract_tenant_id(job.get("metadata")),
                            )
                            logger.warning(f"Job {db_job_id}: Moved to Dead Letter Queue")

                            # F3: Aufrufer über den endgültigen Fehlschlag informieren
                            _enqueue_error_callback(
                                connection,
                                db_job_id,
                                job.get("metadata", {}).get("callback_url"),
                                str(exc),
                                attempts,
                                job,
                                logger,
                            )

                            # F5a: Fehler-Callback zügig versenden
                            _process_pending_callbacks(connection, settings, headers)
                        else:
                            logger.info(f"Job {db_job_id}: Scheduled for retry")

                finally:
                    heartbeat_state["active_jobs"] = max(0, heartbeat_state.get("active_jobs", 0) - 1)
                    worker_context.current_job_id = None

            except KeyboardInterrupt:
                worker_context.should_stop = True
            except Exception:
                logger.exception("Unexpected error in worker loop")
                time.sleep(1)

    finally:
        # F4: Heartbeat-Thread sauber herunterfahren
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=2)

        logger.info("Worker shutting down gracefully...")

        # Deregister from API
        try:
            requests.post(
                f"{settings.api_url}/workers/deregister",
                json={"worker_id": worker_id},
                timeout=5,
                headers=headers,
            )
            logger.info(f"Deregistered worker {worker_id}")
        except requests.RequestException as e:
            logger.error(f"Failed to deregister worker: {e}")

        connection.close()


def _process_pending_callbacks(connection: Any, settings: Settings, headers: dict) -> None:
    """Process pending callbacks with atomic claiming (F5) and auth header (F7)."""
    logger = logging.getLogger(__name__)
    try:
        # F5: Hängengebliebene 'sending'-Claims (Worker-Crash während Versand) re-queueen
        requeue_stale_sending_callbacks(connection, stale_seconds=settings.callback_retry_delay)

        callbacks = fetch_pending_callbacks(connection, limit=5)
        if not callbacks:
            return

        for callback in callbacks:
            callback_id = callback["callback_id"]
            callback_url = callback["callback_url"]
            job_id = callback.get("job_id")
            result_payload = callback["result_payload"]

            # F5b: Atomarer Claim VOR dem Versand - verhindert Doppelversand
            # durch konkurrierende Worker
            if not claim_callback(connection, callback_id):
                continue

            # Parse result_payload if it's a JSON string (SQLite)
            if isinstance(result_payload, str):
                result_payload = json_module.loads(result_payload)

            # Wrap with job_id and status for the callback receiver (F3-Format)
            payload = {
                "job_id": job_id,
                "status": _extract_result_status(result_payload),
                **result_payload,
            }

            # F7: Auth immer via Authorization-Header senden (nie via Query-Parameter);
            # ohne konfigurierten Key wird kein Header gesendet (nur Development).
            send_headers = {"Content-Type": "application/json"}
            if settings.callback_api_key:
                send_headers["Authorization"] = f"Bearer {settings.callback_api_key}"

            attempts_after = (callback.get("attempts") or 0) + 1
            max_attempts = callback.get("max_attempts") or settings.callback_max_attempts

            try:
                response = requests.post(
                    callback_url,
                    json=payload,
                    timeout=10,
                    headers=send_headers,
                )
                success = response.status_code < 300
            except requests.exceptions.RequestException as e:
                # Network error, will retry
                success = False
                logger.warning(f"Callback {callback_id}: Network error, will retry - {e}")

            if success:
                store_callback_result(connection, callback_id, "sent")
                logger.info(f"Callback {callback_id}: Sent successfully")
            elif attempts_after >= max_attempts:
                # F5c: Callback-DLQ - endgültig fehlgeschlagen, sichtbar via API/Monitoring
                store_callback_result(connection, callback_id, "failed")
                logger.warning(
                    f"Callback {callback_id}: Failed permanently after {attempts_after} attempts "
                    f"(job {job_id}, target {callback_url})"
                )
            else:
                store_callback_result(connection, callback_id, "pending")
                logger.warning(
                    f"Callback {callback_id}: Failed, will retry (attempt {attempts_after}/{max_attempts})"
                )

    except Exception:
        logger.exception("Error processing callbacks")
