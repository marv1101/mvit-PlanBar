import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def get_connection(database_url: str) -> sqlite3.Connection:
    parsed = urlparse(database_url)
    if parsed.scheme in ("sqlite", "sqlite3"):
        path = parsed.path or ":memory:"
        if parsed.netloc == "" and path.startswith("/") and path not in ("/:memory:", "/"):
            path = path[1:]
        if path in ("", "/:memory:"):
            path = ":memory:"

        if path != ":memory":
            db_path = Path(path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db_path), check_same_thread=False)
        else:
            conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _initialize_sqlite(conn)
        return conn

    raise ValueError(f"Unsupported database URL scheme: {parsed.scheme}")


def _initialize_sqlite(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS job_queue (
            job_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            status TEXT NOT NULL,
            result TEXT,
            priority INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            last_error TEXT
        )
        """
    )
    connection.commit()


def enqueue_job(connection: sqlite3.Connection, payload: dict, queue_table: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        f"INSERT OR REPLACE INTO {queue_table} (job_id, payload, status, priority, created_at, updated_at, attempts) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            payload["metadata"]["jobId"],
            json.dumps(payload),
            "queued",
            int(payload.get("metadata", {}).get("priority", 0)),
            now,
            now,
            0,
        ),
    )
    connection.commit()


def fetch_next_job(connection: sqlite3.Connection, queue_table: str) -> dict | None:
    cursor = connection.execute(
        f"SELECT * FROM {queue_table} WHERE status = ? ORDER BY priority DESC, created_at ASC LIMIT 1",
        ("queued",),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return json.loads(row["payload"])


def mark_job_processing(connection: sqlite3.Connection, job_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        "UPDATE job_queue SET status = ?, updated_at = ?, attempts = attempts + 1 WHERE job_id = ?",
        ("processing", now, job_id),
    )
    connection.commit()


def store_result(connection: sqlite3.Connection, job_id: str, result: dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        "UPDATE job_queue SET status = ?, result = ?, updated_at = ? WHERE job_id = ?",
        ("completed", json.dumps(result), now, job_id),
    )
    connection.commit()


def count_jobs(connection: sqlite3.Connection, queue_table: str) -> int:
    cursor = connection.execute(f"SELECT COUNT(1) AS count FROM {queue_table}")
    row = cursor.fetchone()
    return int(row["count"])
