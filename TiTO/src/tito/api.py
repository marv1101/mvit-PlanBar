from functools import wraps

from flask import Flask, jsonify, request
from .auth import authenticate_request, authorize_access
from .config import Settings
from .db import (
    count_jobs, enqueue_job, get_connection, register_worker, 
    update_worker_heartbeat, get_workers, fetch_pending_callbacks
)


def create_app(settings: Settings | None = None) -> Flask:
    app = Flask(__name__)
    settings = settings or Settings.from_env()
    connection = get_connection(settings.database_url)

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
                return jsonify({"error": "Unauthorized"}), 401
            if not authorize_access(
                token,
                request.path,
                settings.api_token_roles,
                settings.jwt_secret,
                settings.jwt_algorithms,
                settings.jwt_audience,
                settings.jwt_issuer,
            ):
                return jsonify({"error": "Forbidden"}), 403
            return view(*args, **kwargs)
        return decorated

    @app.get("/health")
    def health_check():
        return jsonify({"status": "ok"})

    @app.get("/metrics")
    @require_auth
    def metrics():
        workers = get_workers(connection)
        return jsonify({
            "queue_length": count_jobs(connection, settings.queue_table),
            "active_workers": len(workers),
            "workers": workers
        })

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
            return jsonify({"error": "Invalid JSON payload"}), 400

        # Extract PHASE 4 robustness parameters from metadata
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
            return jsonify({"error": "Duplicate job (idempotency_key already exists)", "status": "duplicate"}), 409
        
        return jsonify({"status": "queued", "jobId": job_id}), 201

    @app.post("/workers/register")
    @require_auth
    def register_worker_endpoint():
        data = request.get_json(silent=True)
        if not data or 'worker_id' not in data:
            return jsonify({"error": "Invalid payload"}), 400
        worker_id = data['worker_id']
        ip = request.remote_addr or "unknown"
        cpu_usage = data.get('cpu_usage', 0.0)
        ram_usage = data.get('ram_usage', 0.0)
        register_worker(connection, worker_id, ip, cpu_usage, ram_usage)
        return jsonify({"status": "registered"})

    @app.post("/workers/heartbeat")
    @require_auth
    def heartbeat_endpoint():
        data = request.get_json(silent=True)
        if not data or 'worker_id' not in data:
            return jsonify({"error": "Invalid payload"}), 400
        worker_id = data['worker_id']
        cpu_usage = data.get('cpu_usage', 0.0)
        ram_usage = data.get('ram_usage', 0.0)
        active_jobs = data.get('active_jobs', 0)
        update_worker_heartbeat(connection, worker_id, cpu_usage, ram_usage, active_jobs)
        return jsonify({"status": "updated"})
    
    @app.get("/dlq")
    @require_auth
    def get_dlq():
        """Get jobs in Dead Letter Queue"""
        cursor = connection.execute(
            "SELECT dlq_id, job_id, original_payload, failure_reason, sent_to_dlq_at, attempts FROM dead_letter_queue ORDER BY sent_to_dlq_at DESC"
        )
        dlq_jobs = [dict(row) for row in cursor.fetchall()]
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
        cursor = connection.execute(
            f"""SELECT job_id, status, attempts, max_retries, last_error, failed_at, 
                      scheduled_for, callback_url, result FROM {settings.queue_table} WHERE job_id = ?""",
            (job_id,)
        )
        job = cursor.fetchone()
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        job_data = dict(job)
        
        # Get callback status if exists
        cursor = connection.execute(
            "SELECT callback_id, callback_status, attempts, max_attempts FROM callback_queue WHERE job_id = ?",
            (job_id,)
        )
        callback = cursor.fetchone()
        if callback:
            job_data["callback"] = dict(callback)
        
        return jsonify(job_data)
    
    @app.post("/jobs/<int:job_id>/retry")
    @require_auth
    def manual_retry_job(job_id):
        """Manually retry a failed job"""
        cursor = connection.execute(
            f"SELECT status, attempts, max_retries FROM {settings.queue_table} WHERE job_id = ?",
            (job_id,)
        )
        job = cursor.fetchone()
        
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        if job["status"] not in ("failed", "dead_lettered"):
            return jsonify({"error": f"Cannot retry job in {job['status']} status"}), 400
        
        # Reset to queued status
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        connection.execute(
            f"UPDATE {settings.queue_table} SET status = ?, updated_at = ?, scheduled_for = NULL WHERE job_id = ?",
            ("queued", now, job_id)
        )
        connection.commit()
        
        return jsonify({"status": "retry_scheduled", "jobId": job_id})
    
    @app.get("/metrics/robustness")
    @require_auth
    def robustness_metrics():
        """Get robustness metrics: retries, DLQ, callbacks"""
        cursor = connection.execute(
            f"SELECT status, COUNT(*) as count FROM {settings.queue_table} GROUP BY status"
        )
        status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}
        
        cursor = connection.execute("SELECT COUNT(*) as count FROM dead_letter_queue")
        dlq_count = cursor.fetchone()["count"]
        
        cursor = connection.execute(
            "SELECT callback_status, COUNT(*) as count FROM callback_queue GROUP BY callback_status"
        )
        callback_counts = {row["callback_status"]: row["count"] for row in cursor.fetchall()}
        
        return jsonify({
            "job_statuses": status_counts,
            "dead_letter_queue_size": dlq_count,
            "callbacks": callback_counts
        })

    return app
