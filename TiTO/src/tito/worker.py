import json as json_module
import time
import uuid
import psutil
import requests
import signal
import logging
from datetime import datetime, timezone
from typing import Any
from .config import Settings
from .db import (
    get_connection, fetch_next_job, mark_job_processing, store_result,
    mark_job_failed_with_retry, move_job_to_dlq, check_job_timeout,
    enqueue_callback, check_idempotency, fetch_pending_callbacks, store_callback_result
)
from .schema import validate_job_payload, JobPayload
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


def run_worker(settings: Settings) -> None:
    """Hauptschleife des TiTO-Workers mit Robustness-Features."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    logger.info("Starting TiTO Worker...")
    worker_id = str(uuid.uuid4())
    logger.info(f"Worker ID: {worker_id}")
    
    # Setup graceful shutdown
    worker_context = WorkerContext()
    signal.signal(signal.SIGTERM, worker_context.request_stop)
    signal.signal(signal.SIGINT, worker_context.request_stop)
    
    # Sammle initiale Stats
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    
    # Registriere bei der API
    headers = {}
    if settings.api_tokens:
        headers["Authorization"] = f"Bearer {settings.api_tokens[0]}"

    try:
        requests.post(f"{settings.api_url}/workers/register", json={
            "worker_id": worker_id,
            "cpu_usage": cpu,
            "ram_usage": ram
        }, timeout=5, headers=headers)
    except Exception as e:
        logger.error(f"Failed to register worker: {e}")
    
    connection = get_connection(settings.database_url)
    active_jobs = 0
    last_heartbeat_time = time.time()
    
    while not worker_context.should_stop:
        try:
            # Sende Heartbeat alle 5 Sekunden
            if time.time() - last_heartbeat_time >= 5:
                last_heartbeat_time = time.time()
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().percent
                try:
                    requests.post(f"{settings.api_url}/workers/heartbeat", json={
                        "worker_id": worker_id,
                        "cpu_usage": cpu,
                        "ram_usage": ram,
                        "active_jobs": active_jobs
                    }, timeout=5, headers=headers)
                except Exception as e:
                    logger.error(f"Failed to send heartbeat: {e}")

            # Process job queue
            job = fetch_next_job(connection, settings.queue_table)
            if job is None:
                # No job available, process callbacks instead
                _process_pending_callbacks(connection, settings, headers)
                time.sleep(1)
                continue
            
            active_jobs += 1
            db_job_id = job.pop("_db_job_id")
            worker_context.current_job_id = db_job_id
            
            try:
                # check idempotency - prevent duplicate processing
                idempotency_key = job.get("metadata", {}).get("idempotency_key")
                if idempotency_key:
                    existing_job = check_idempotency(connection, idempotency_key)
                    if existing_job and existing_job["status"] == "completed":
                        logger.info(f"Job {db_job_id}: Skipping duplicate (idempotency_key: {idempotency_key})")
                        # Still enqueue callback for the duplicate
                        if job.get("metadata", {}).get("callback_url"):
                            enqueue_callback(
                                connection, db_job_id,
                                job["metadata"]["callback_url"],
                                existing_job.get("result", {})
                            )
                        continue
                
                # Mark job as processing and set timeout
                mark_job_processing(connection, db_job_id)
                logger.info(f"Processing job ID: {db_job_id}")

                # Validate payload and get Pydantic model
                job_payload: JobPayload = validate_job_payload(job)
                
                # Build and solve model (with timeout)
                model = build_model(job_payload.model_dump())
                result = solve_model(model, settings.timeout_seconds)

                # Store successful result
                store_result(connection, db_job_id, result)
                logger.info(f"Job {db_job_id}: Completed successfully")
                
                # enqueue callback if requested
                callback_url = job.get("metadata", {}).get("callback_url")
                if callback_url:
                    enqueue_callback(
                        connection, db_job_id, callback_url, result,
                        tenant_id=job.get("metadata", {}).get("tenant_id")
                    )
                    logger.info(f"Job {db_job_id}: Callback enqueued")
                
            except Exception as exc:
                logger.error(f"Job {db_job_id} failed: {exc}")
                
                #try to retry with exponential backoff
                will_retry = mark_job_failed_with_retry(connection, db_job_id, str(exc))
                
                if not will_retry:
                    # Max retries exceeded, move to DLQ
                    move_job_to_dlq(
                        connection, db_job_id, job,
                        f"Max retries exceeded: {exc}",
                        attempts=3,
                        tenant_id=job.get("metadata", {}).get("tenant_id")
                    )
                    logger.warning(f"Job {db_job_id}: Moved to Dead Letter Queue")
                else:
                    logger.info(f"Job {db_job_id}: Scheduled for retry")
            
            finally:
                active_jobs -= 1
                worker_context.current_job_id = None
        
        except KeyboardInterrupt:
            worker_context.should_stop = True
        except Exception as e:
            logger.error(f"Unexpected error in worker loop: {e}")
            time.sleep(1)
    
    logger.info("Worker shutting down gracefully...")
    
    # Deregister from API
    try:
        requests.post(f"{settings.api_url}/workers/deregister", json={
            "worker_id": worker_id
        }, timeout=5, headers=headers)
        logger.info(f"Deregistered worker {worker_id}")
    except Exception as e:
        logger.error(f"Failed to deregister worker: {e}")
    
    connection.close()


def _process_pending_callbacks(
    connection: Any,
    settings: Settings,
    headers: dict
) -> None:
    """Process pending callbacks and retry sending them."""
    logger = logging.getLogger(__name__)
    try:
        callbacks = fetch_pending_callbacks(connection, limit=5)
        if not callbacks:
            return
        
        for callback in callbacks:
            callback_id = callback["callback_id"]
            callback_url = callback["callback_url"]
            job_id = callback.get("job_id")
            result_payload = callback["result_payload"]
            
            # Parse result_payload if it's a JSON string (SQLite)
            if isinstance(result_payload, str):
                result_payload = json_module.loads(result_payload)
            
            # Wrap with job_id and status for the callback receiver
            payload = {
                "job_id": job_id,
                "status": result_payload.get("metadata", {}).get("status", "unknown"),
                **result_payload,
            }
            
            try:
                response = requests.post(
                    callback_url,
                    json=payload,
                    timeout=10,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code < 300:
                    # Success
                    store_callback_result(connection, callback_id, "sent")
                    logger.info(f"Callback {callback_id}: Sent successfully")
                else:
                    # Failure but will retry
                    store_callback_result(connection, callback_id, "pending")
                    logger.warning(f"Callback {callback_id}: Failed (HTTP {response.status_code}), will retry")
            
            except requests.exceptions.RequestException as e:
                # Network error, will retry
                store_callback_result(connection, callback_id, "pending")
                logger.warning(f"Callback {callback_id}: Network error, will retry - {e}")
    
    except Exception as e:
        logger.error(f"Error processing callbacks: {e}")
