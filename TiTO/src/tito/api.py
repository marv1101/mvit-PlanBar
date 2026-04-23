from flask import Flask, jsonify, request
from .config import Settings
from .db import count_jobs, enqueue_job, get_connection


def create_app(settings: Settings | None = None) -> Flask:
    app = Flask(__name__)
    settings = settings or Settings.from_env()
    connection = get_connection(settings.database_url)

    @app.get("/health")
    def health_check():
        return jsonify({"status": "ok"})

    @app.get("/metrics")
    def metrics():
        return jsonify({"queue_length": count_jobs(connection, settings.queue_table), "active_workers": 0})

    @app.get("/jobs")
    def list_jobs():
        cursor = connection.execute(f"SELECT job_id, status, priority, created_at, updated_at FROM {settings.queue_table} ORDER BY created_at DESC")
        jobs = [dict(row) for row in cursor.fetchall()]
        return jsonify(jobs)

    @app.post("/jobs")
    def post_job():
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({"error": "Invalid JSON payload"}), 400

        enqueue_job(connection, payload, settings.queue_table)
        return jsonify({"status": "queued", "jobId": payload.get("metadata", {}).get("jobId")}), 201

    return app
