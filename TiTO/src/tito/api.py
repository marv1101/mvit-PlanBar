from functools import wraps
import threading
import time
import logging

from flask import Flask, Response, jsonify, request
from .auth import authenticate_request, authorize_access
from .config import Settings
from .db import (
    count_jobs, enqueue_job, fetch_callback_count_grouped_by_status, fetch_dlq_count, fetch_jobs_grouped_by_status, get_connection, register_worker, 
    update_worker_heartbeat, get_workers, fetch_pending_callbacks,
    fetch_dlq_jobs, fetch_job_status_by_id, fetch_callback_status_by_job_id,
    fetch_job_by_id, update_job, deregister_worker, cleanup_inactive_workers
)
from . import monitoring


def cleanup_worker_thread(connection, interval_minutes: int = 5):
    """Background thread that periodically cleans up inactive workers."""
    while True:
        try:
            deleted_count = cleanup_inactive_workers(connection, timeout_seconds=300)  # 5 minutes
            if deleted_count > 0:
                print(f"[Cleanup] Removed {deleted_count} inactive workers")
        except Exception as e:
            print(f"[Cleanup] Error during cleanup: {e}")
        time.sleep(interval_minutes * 60)


def create_app(settings: Settings | None = None) -> Flask:
    app = Flask(__name__)
    settings = settings or Settings.from_env()
    connection = get_connection(settings.database_url)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Start background cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_worker_thread, args=(connection,), daemon=True)
    cleanup_thread.start()

    def require_auth(view):
        @wraps(view)
        def decorated(*args, **kwargs):
            token = None
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
            if not token:
                token = request.headers.get("X-API-Key")

            if not authenticate_request(
                token,
                settings.api_tokens,
                settings.jwt_secret,
                settings.jwt_algorithms,
                settings.jwt_audience,
                settings.jwt_issuer,
            ):
                logger.warning(f"Authentication failed for request to {request.path}")
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Invalid or missing authentication token",
                    "status_code": 401
                }), 401
            if not authorize_access(
                token,
                request.path,
                settings.api_token_roles,
                settings.jwt_secret,
                settings.jwt_algorithms,
                settings.jwt_audience,
                settings.jwt_issuer,
            ):
                logger.warning(f"Authorization failed for request to {request.path}")
                return jsonify({
                    "error": "Forbidden",
                    "message": "Insufficient permissions for this resource",
                    "status_code": 403
                }), 403
            return view(*args, **kwargs)
        return decorated

    @app.get("/health")
    def health_check():
        return jsonify({"status": "ok"})

    @app.get("/metrics")
    @require_auth
    def metrics():
        metrics_data = monitoring.get_metrics(connection, settings.queue_table, settings.timeout_seconds)
        return jsonify(metrics_data)

    @app.get("/jobs")
    @require_auth
    def list_jobs():
        cursor = connection.execute(f"SELECT job_id, status, priority, created_at, updated_at FROM {settings.queue_table} ORDER BY created_at DESC")
        jobs = [dict(row) for row in cursor.fetchall()]
        return jsonify(jobs)

    @app.post("/jobs")
    @require_auth
    def post_job():
        payload = request.get_json(silent=True)
        if not payload:
            logger.warning("Invalid JSON payload received")
            return jsonify({
                "error": "Invalid request",
                "message": "Request body must be valid JSON",
                "status_code": 400
            }), 400

        # Extract parameters from metadata
        metadata = payload.get("metadata", {})
        idempotency_key = metadata.get("idempotency_key")
        callback_url = metadata.get("callback_url")
        max_retries = int(metadata.get("max_retries", settings.max_retries))
        tenant_id = metadata.get("tenant_id")

        job_id = enqueue_job(
            connection, payload, settings.queue_table,
            idempotency_key=idempotency_key,
            callback_url=callback_url,
            max_retries=max_retries,
            tenant_id=tenant_id
        )
        
        if job_id is None:
            # Duplicate job with idempotency_key
            logger.info(f"Duplicate job rejected with idempotency_key: {idempotency_key}")
            return jsonify({
                "error": "Duplicate job",
                "message": "A job with the same idempotency_key already exists",
                "status_code": 409
            }), 409
        
        logger.info(f"Job {job_id} queued successfully")
        return jsonify({"status": "queued", "jobId": job_id}), 201

    @app.post("/workers/register")
    @require_auth
    def register_worker_endpoint():
        data = request.get_json(silent=True)
        if not data or 'worker_id' not in data:
            logger.warning("Invalid worker registration payload")
            return jsonify({
                "error": "Invalid request",
                "message": "worker_id is required",
                "status_code": 400
            }), 400
        worker_id = data['worker_id']
        ip = request.remote_addr or "unknown"
        cpu_usage = data.get('cpu_usage', 0.0)
        ram_usage = data.get('ram_usage', 0.0)
        register_worker(connection, worker_id, ip, cpu_usage, ram_usage)
        logger.info(f"Worker {worker_id} registered")
        return jsonify({"status": "registered"})

    @app.post("/workers/heartbeat")
    @require_auth
    def heartbeat_endpoint():
        data = request.get_json(silent=True)
        if not data or 'worker_id' not in data:
            logger.warning("Invalid heartbeat payload")
            return jsonify({
                "error": "Invalid request",
                "message": "worker_id is required",
                "status_code": 400
            }), 400
        worker_id = data['worker_id']
        cpu_usage = data.get('cpu_usage', 0.0)
        ram_usage = data.get('ram_usage', 0.0)
        active_jobs = data.get('active_jobs', 0)
        update_worker_heartbeat(connection, worker_id, cpu_usage, ram_usage, active_jobs)
        return jsonify({"status": "updated"})
    
    @app.post("/workers/deregister")
    @require_auth
    def deregister_endpoint():
        data = request.get_json(silent=True)
        if not data or 'worker_id' not in data:
            logger.warning("Invalid deregister payload")
            return jsonify({
                "error": "Invalid request",
                "message": "worker_id is required",
                "status_code": 400
            }), 400
        worker_id = data['worker_id']
        deregister_worker(connection, worker_id)
        logger.info(f"Worker {worker_id} deregistered")
        return jsonify({"status": "deregistered"})
    
    @app.post("/workers/cleanup")
    @require_auth
    def cleanup_endpoint():
        timeout_seconds = request.args.get('timeout', default=300, type=int)
        deleted_count = cleanup_inactive_workers(connection, timeout_seconds)
        return jsonify({"status": "cleanup completed", "deleted_workers": deleted_count})
    
    @app.get("/dlq")
    @require_auth
    def get_dlq():
        dlq_jobs = fetch_dlq_jobs(connection, limit=50)
        return jsonify({"count": len(dlq_jobs), "jobs": dlq_jobs})
    
    @app.get("/callbacks/pending")
    @require_auth
    def get_pending_callbacks():
        """Get pending callbacks to be sent"""
        callbacks = fetch_pending_callbacks(connection, limit=50)
        return jsonify({"count": len(callbacks), "callbacks": callbacks})
    
    @app.get("/jobs/<int:job_id>")
    @require_auth
    def get_job_status(job_id):
        """Get detailed job status including retry attempts and callbacks"""
        job = fetch_job_status_by_id(connection, job_id)
        
        if not job:
            logger.warning(f"Job {job_id} not found")
            return jsonify({
                "error": "Not found",
                "message": f"Job {job_id} does not exist",
                "status_code": 404
            }), 404
        
        job_data = dict(job)
        
        # Get callback status if exists
        callback = fetch_callback_status_by_job_id(connection, job_id)
        if callback:
            job_data["callback"] = callback
        
        return jsonify(job_data)
    
    @app.post("/jobs/<int:job_id>/retry")
    @require_auth
    def manual_retry_job(job_id):
        """Manually retry a failed job"""

        job = fetch_job_by_id(connection, job_id)
        
        if not job:
            logger.warning(f"Attempted to retry non-existent job {job_id}")
            return jsonify({
                "error": "Not found",
                "message": f"Job {job_id} does not exist",
                "status_code": 404
            }), 404
        
        if job["status"] not in ("failed", "dead_lettered"):
            logger.warning(f"Cannot retry job {job_id} in status {job['status']}")
            return jsonify({
                "error": "Invalid operation",
                "message": f"Cannot retry job in {job['status']} status",
                "status_code": 400
            }), 400
        
        # Reset to queued status
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()

        update_job(connection, job_id, status="queued")
        logger.info(f"Job {job_id} manually retried")
        return jsonify({"status": "retry_scheduled", "jobId": job_id})
    
    @app.get("/metrics/robustness")
    @require_auth
    def robustness_metrics():
        """Get robustness metrics: retries, DLQ, callbacks"""
        metrics_data = monitoring.get_metrics(connection, settings.queue_table, settings.timeout_seconds)
        return jsonify({
            "job_statuses": metrics_data["job_status_counts"],
            "dead_letter_queue_size": metrics_data["dead_letter_queue_size"],
            "callbacks": metrics_data["callback_counts"],
            "error_rate": metrics_data["error_rate"],
            "solver_timeout_rate": metrics_data["solver_timeout_rate"],
            "average_job_duration_seconds": metrics_data["average_job_duration_seconds"],
        })

    @app.get("/metrics/prometheus")
    @require_auth
    def prometheus_metrics():
        text = monitoring.export_prometheus(connection, settings.queue_table, settings.timeout_seconds)
        return Response(text, mimetype="text/plain; version=0.0.4")

    return app
