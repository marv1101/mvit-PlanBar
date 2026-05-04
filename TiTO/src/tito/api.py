from functools import wraps

from flask import Flask, jsonify, request
from .auth import authenticate_request, authorize_access
from .config import Settings
from .db import count_jobs, enqueue_job, get_connection, register_worker, update_worker_heartbeat, get_workers


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

        job_id = enqueue_job(connection, payload, settings.queue_table)
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

    return app
