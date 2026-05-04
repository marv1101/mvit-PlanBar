import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import pool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


# Global PostgreSQL connection pool
_pg_pool: Any = None


def get_connection(database_url: str) -> sqlite3.Connection | psycopg2.extensions.connection:
    """Get database connection (SQLite or PostgreSQL)."""
    parsed = urlparse(database_url)
    
    # PostgreSQL support
    if parsed.scheme in ("postgresql", "postgres"):
        if not PSYCOPG2_AVAILABLE:
            raise ImportError("psycopg2 is required for PostgreSQL support")
        return _get_postgres_connection(database_url)
    
    # SQLite support
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


def _get_postgres_connection(database_url: str) -> psycopg2.extensions.connection:
    """Get PostgreSQL connection with proper configuration."""
    global _pg_pool
    
    # Remove the scheme prefix for psycopg2
    db_url = database_url.replace("postgresql://", "").replace("postgres://", "")
    
    conn = psycopg2.connect(database_url)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    
    # Set cursor factory to return dictionaries
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    
    _initialize_postgres(conn)
    return conn


def _initialize_sqlite(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS job_queue (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload TEXT NOT NULL,
            status TEXT NOT NULL,
            result TEXT,
            priority INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            last_error TEXT,
            failed_at TEXT,
            scheduled_for TEXT,
            callback_url TEXT,
            idempotency_key TEXT UNIQUE,
            timeout_at TEXT,
            tenant_id TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS dead_letter_queue (
            dlq_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            original_payload TEXT NOT NULL,
            failure_reason TEXT NOT NULL,
            sent_to_dlq_at TEXT NOT NULL,
            attempts INTEGER NOT NULL,
            tenant_id TEXT,
            FOREIGN KEY(job_id) REFERENCES job_queue(job_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS callback_queue (
            callback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            callback_url TEXT NOT NULL,
            callback_status TEXT DEFAULT 'pending',
            result_payload TEXT,
            created_at TEXT NOT NULL,
            attempted_at TEXT,
            attempts INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 3,
            tenant_id TEXT,
            FOREIGN KEY(job_id) REFERENCES job_queue(job_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS workers (
            worker_id TEXT PRIMARY KEY,
            ip TEXT NOT NULL,
            registered_at TEXT NOT NULL,
            last_heartbeat TEXT NOT NULL,
            cpu_usage REAL,
            ram_usage REAL,
            active_jobs INTEGER DEFAULT 0
        )
        """
    )
    connection.commit()


def _initialize_postgres(connection: psycopg2.extensions.connection) -> None:
    """Initialize PostgreSQL database schema."""
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS job_queue (
                job_id SERIAL PRIMARY KEY,
                payload JSONB NOT NULL,
                status TEXT NOT NULL,
                result JSONB,
                priority INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                attempts INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                last_error TEXT,
                failed_at TIMESTAMP WITH TIME ZONE,
                scheduled_for TIMESTAMP WITH TIME ZONE,
                callback_url TEXT,
                idempotency_key TEXT UNIQUE,
                timeout_at TIMESTAMP WITH TIME ZONE,
                tenant_id TEXT
            )
            """
        )
        
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dead_letter_queue (
                dlq_id SERIAL PRIMARY KEY,
                job_id INTEGER NOT NULL,
                original_payload JSONB NOT NULL,
                failure_reason TEXT NOT NULL,
                sent_to_dlq_at TIMESTAMP WITH TIME ZONE NOT NULL,
                attempts INTEGER NOT NULL,
                tenant_id TEXT,
                FOREIGN KEY(job_id) REFERENCES job_queue(job_id) ON DELETE CASCADE
            )
            """
        )
        
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS callback_queue (
                callback_id SERIAL PRIMARY KEY,
                job_id INTEGER NOT NULL,
                callback_url TEXT NOT NULL,
                callback_status TEXT DEFAULT 'pending',
                result_payload JSONB,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                attempted_at TIMESTAMP WITH TIME ZONE,
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 3,
                tenant_id TEXT,
                FOREIGN KEY(job_id) REFERENCES job_queue(job_id) ON DELETE CASCADE
            )
            """
        )
        
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS workers (
                worker_id TEXT PRIMARY KEY,
                ip TEXT NOT NULL,
                registered_at TIMESTAMP WITH TIME ZONE NOT NULL,
                last_heartbeat TIMESTAMP WITH TIME ZONE NOT NULL,
                cpu_usage REAL,
                ram_usage REAL,
                active_jobs INTEGER DEFAULT 0
            )
            """
        )
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_queue_status ON job_queue(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_queue_scheduled_for ON job_queue(scheduled_for)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_queue_idempotency_key ON job_queue(idempotency_key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_callback_queue_status ON callback_queue(callback_status)")
        
        connection.commit()
    finally:
        cursor.close()


def enqueue_job(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    payload: dict,
    queue_table: str,
    idempotency_key: str | None = None,
    callback_url: str | None = None,
    max_retries: int = 3,
    tenant_id: str | None = None
) -> int | None:
    """
    Enqueue a new job with robustness features.
    
    Args:
        connection: Database connection
        payload: Job payload
        queue_table: Queue table name
        idempotency_key: Optional idempotency key to prevent duplicate processing
        callback_url: Optional URL to call when job completes
        max_retries: Maximum number of retries (default 3)
        tenant_id: Optional tenant ID for multi-tenancy
    
    Returns:
        Job ID if successful, None if duplicate (idempotency)
    """
    now = datetime.now(timezone.utc)
    priority = int(payload.get("metadata", {}).get("priority", 0))
    
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        
        # If idempotency_key provided, check for duplicate
        if idempotency_key:
            cursor.execute(
                "SELECT job_id, status FROM job_queue WHERE idempotency_key = %s",
                (idempotency_key,)
            )
            existing = cursor.fetchone()
            if existing:
                print(f"[DB] Duplicate job detected with idempotency_key: {idempotency_key}")
                cursor.close()
                return None  # Return None to indicate duplicate
        
        cursor.execute(
            """INSERT INTO job_queue 
               (payload, status, priority, created_at, updated_at, attempts, max_retries, 
                callback_url, idempotency_key, tenant_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING job_id""",
            (
                json.dumps(payload),
                "queued",
                priority,
                now,
                now,
                0,
                max_retries,
                callback_url,
                idempotency_key,
                tenant_id
            )
        )
        job_id = cursor.fetchone()[0]
        connection.commit()
        cursor.close()
        return job_id
    else:
        # SQLite
        if idempotency_key:
            cursor = connection.execute(
                "SELECT job_id, status FROM job_queue WHERE idempotency_key = ?",
                (idempotency_key,)
            )
            existing = cursor.fetchone()
            if existing:
                print(f"[DB] Duplicate job detected with idempotency_key: {idempotency_key}")
                return None  # Return None to indicate duplicate
        
        cursor = connection.execute(
            """INSERT INTO job_queue 
               (payload, status, priority, created_at, updated_at, attempts, max_retries, 
                callback_url, idempotency_key, tenant_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                json.dumps(payload),
                "queued",
                priority,
                now.isoformat(),
                now.isoformat(),
                0,
                max_retries,
                callback_url,
                idempotency_key,
                tenant_id
            )
        )
        job_id = cursor.lastrowid
        connection.commit()
        return job_id

def fetch_job_by_id(connection: sqlite3.Connection | psycopg2.extensions.connection, job_id: int) -> dict | None:
    """Fetch job details by job ID."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            "SELECT * FROM job_queue WHERE job_id = %s",
            (job_id,)
        )
        job = cursor.fetchone()
        cursor.close()
        
        if job is None:
            return None
        
        return dict(job)
    else:
        # SQLite
        cursor = connection.execute(
            "SELECT * FROM job_queue WHERE job_id = ?",
            (job_id,)
        )
        job = cursor.fetchone()
        
        if job is None:
            return None

        return dict(job)

def fetch_job_status_by_id(connection: sqlite3.Connection | psycopg2.extensions.connection, job_id: int) -> dict | None:
    """Fetch job status and details by job ID."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            "SELECT job_id, status, result, attempts, max_retries, last_error FROM job_queue WHERE job_id = %s",
            (job_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        
        if row is None:
            return None
        
        return {
            "job_id": row["job_id"],
            "status": row["status"],
            "result": row["result"],
            "attempts": row["attempts"],
            "max_retries": row["max_retries"],
            "last_error": row["last_error"]
        }
    else:
        # SQLite
        cursor = connection.execute(
            "SELECT job_id, status, result, attempts, max_retries, last_error FROM job_queue WHERE job_id = ?",
            (job_id,)
        )
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return {
            "job_id": row["job_id"],
            "status": row["status"],
            "result": json.loads(row["result"]) if row["result"] else None,
            "attempts": row["attempts"],
            "max_retries": row["max_retries"],
            "last_error": row["last_error"]
        }

def fetch_next_job(connection: sqlite3.Connection | psycopg2.extensions.connection, queue_table: str) -> dict | None:
    """Fetch next job from queue (FIFO with priority). Handles both SQLite and PostgreSQL."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            f"""SELECT * FROM {queue_table} 
               WHERE status = 'queued' AND (scheduled_for IS NULL OR scheduled_for <= NOW() AT TIME ZONE 'UTC')
               ORDER BY priority DESC, created_at ASC LIMIT 1"""
        )
        row = cursor.fetchone()
        cursor.close()
        
        if row is None:
            return None
        
        payload = row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"])
        payload["_db_job_id"] = row["job_id"]
        return payload
    else:
        # SQLite
        cursor = connection.execute(
            f"""SELECT * FROM {queue_table} 
               WHERE status = 'queued' AND (scheduled_for IS NULL OR scheduled_for <= datetime('now'))
               ORDER BY priority DESC, created_at ASC LIMIT 1"""
        )
        row = cursor.fetchone()
        if row is None:
            return None
        
        payload = json.loads(row["payload"])
        payload["_db_job_id"] = row["job_id"]
        return payload


def mark_job_processing(connection: sqlite3.Connection | psycopg2.extensions.connection, job_id: int) -> None:
    """Mark job as processing. Increments attempts counter."""
    now = datetime.now(timezone.utc)
    
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """UPDATE job_queue SET status = %s, updated_at = %s, attempts = attempts + 1 WHERE job_id = %s""",
            ("processing", now, job_id)
        )
        connection.commit()
        cursor.close()
    else:
        # SQLite
        connection.execute(
            "UPDATE job_queue SET status = ?, updated_at = ?, attempts = attempts + 1 WHERE job_id = ?",
            ("processing", now.isoformat(), job_id),
        )
        connection.commit()

def update_job(connection: sqlite3.Connection | psycopg2.extensions.connection, job_id: int, status: str, result: dict | None = None, error: str | None = None) -> None:
    """Update job status, result and error information."""
    now = datetime.now(timezone.utc)
    
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """UPDATE job_queue SET status = %s, result = %s, last_error = %s, updated_at = %s WHERE job_id = %s""",
            (status, json.dumps(result) if result else None, error, now, job_id)
        )
        connection.commit()
        cursor.close()
    else:
        # SQLite
        connection.execute(
            "UPDATE job_queue SET status = ?, result = ?, last_error = ?, updated_at = ? WHERE job_id = ?",
            (status, json.dumps(result) if result else None, error, now.isoformat(), job_id),
        )
        connection.commit()

def store_result(connection: sqlite3.Connection | psycopg2.extensions.connection, job_id: int, result: dict) -> None:
    """Store job result and mark as completed."""
    now = datetime.now(timezone.utc)
    
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """UPDATE job_queue SET status = %s, result = %s, updated_at = %s WHERE job_id = %s""",
            ("completed", json.dumps(result), now, job_id)
        )
        connection.commit()
        cursor.close()
    else:
        # SQLite
        connection.execute(
            "UPDATE job_queue SET status = ?, result = ?, updated_at = ? WHERE job_id = ?",
            ("completed", json.dumps(result), now.isoformat(), job_id),
        )
        connection.commit()


def count_jobs(connection: sqlite3.Connection, queue_table: str) -> int:
    cursor = connection.execute(f"SELECT COUNT(1) AS count FROM {queue_table}")
    row = cursor.fetchone()
    return int(row["count"])


def register_worker(connection: sqlite3.Connection, worker_id: str, ip: str, cpu_usage: float, ram_usage: float) -> None:
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        "INSERT OR REPLACE INTO workers (worker_id, ip, registered_at, last_heartbeat, cpu_usage, ram_usage, active_jobs) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (worker_id, ip, now, now, cpu_usage, ram_usage, 0),
    )
    connection.commit()


def update_worker_heartbeat(connection: sqlite3.Connection, worker_id: str, cpu_usage: float, ram_usage: float, active_jobs: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        "UPDATE workers SET last_heartbeat = ?, cpu_usage = ?, ram_usage = ?, active_jobs = ? WHERE worker_id = ?",
        (now, cpu_usage, ram_usage, active_jobs, worker_id),
    )
    connection.commit()


def get_workers(connection: sqlite3.Connection) -> list[dict]:
    cursor = connection.execute("SELECT * FROM workers ORDER BY registered_at DESC")
    return [dict(row) for row in cursor.fetchall()]


def count_workers(connection: sqlite3.Connection) -> int:
    cursor = connection.execute("SELECT COUNT(1) AS count FROM workers")
    row = cursor.fetchone()
    return int(row["count"])

def mark_job_failed_with_retry(
    connection: sqlite3.Connection | psycopg2.extensions.connection, 
    job_id: int, 
    error: str,
    base_delay: int = 5
) -> bool:
    """
    Mark job as failed and schedule retry with exponential backoff.
    Returns True if job will be retried, False if max retries exceeded (move to DLQ).
    
    Backoff calculation: base_delay * (2 ^ attempts) seconds
    """
    now = datetime.now(timezone.utc)
    
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        
        # Get current attempt count and max_retries
        cursor.execute(
            "SELECT attempts, max_retries FROM job_queue WHERE job_id = %s",
            (job_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        
        if row is None:
            return False
        
        attempts = row["attempts"]
        max_retries = row["max_retries"] or 3
        
        if attempts >= max_retries:
            # Max retries exceeded, don't schedule retry
            cursor = connection.cursor()
            cursor.execute(
                """UPDATE job_queue SET status = %s, failed_at = %s, last_error = %s, updated_at = %s 
                   WHERE job_id = %s""",
                ("failed", now, error, now, job_id)
            )
            connection.commit()
            cursor.close()
            return False
        
        # Schedule retry with exponential backoff
        backoff_seconds = base_delay * (2 ** attempts)
        scheduled_for = datetime.fromtimestamp(now.timestamp() + backoff_seconds, tz=timezone.utc)
        
        cursor = connection.cursor()
        cursor.execute(
            """UPDATE job_queue SET status = %s, scheduled_for = %s, last_error = %s, updated_at = %s 
               WHERE job_id = %s""",
            ("queued", scheduled_for, error, now, job_id)
        )
        connection.commit()
        cursor.close()
        return True
    else:
        # SQLite
        cursor = connection.execute(
            "SELECT attempts, max_retries FROM job_queue WHERE job_id = ?",
            (job_id,)
        )
        row = cursor.fetchone()
        
        if row is None:
            return False
        
        attempts = row["attempts"]
        max_retries = row["max_retries"] or 3
        
        if attempts >= max_retries:
            connection.execute(
                "UPDATE job_queue SET status = ?, failed_at = ?, last_error = ?, updated_at = ? WHERE job_id = ?",
                ("failed", now.isoformat(), error, now.isoformat(), job_id)
            )
            connection.commit()
            return False
        
        backoff_seconds = base_delay * (2 ** attempts)
        scheduled_for = datetime.fromtimestamp(now.timestamp() + backoff_seconds, tz=timezone.utc)
        
        connection.execute(
            "UPDATE job_queue SET status = ?, scheduled_for = ?, last_error = ?, updated_at = ? WHERE job_id = ?",
            ("queued", scheduled_for.isoformat(), error, now.isoformat(), job_id)
        )
        connection.commit()
        return True


def move_job_to_dlq(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    job_id: int,
    original_payload: dict,
    failure_reason: str,
    attempts: int,
    tenant_id: str | None = None
) -> int | None:
    """Move permanently failed job to Dead Letter Queue. Returns DLQ ID."""
    now = datetime.now(timezone.utc)
    
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO dead_letter_queue 
               (job_id, original_payload, failure_reason, sent_to_dlq_at, attempts, tenant_id)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING dlq_id""",
            (job_id, json.dumps(original_payload), failure_reason, now, attempts, tenant_id)
        )
        dlq_id = cursor.fetchone()[0]
        
        # Mark job as dead_lettered
        cursor.execute(
            "UPDATE job_queue SET status = %s, updated_at = %s WHERE job_id = %s",
            ("dead_lettered", now, job_id)
        )
        connection.commit()
        cursor.close()
        return dlq_id
    else:
        # SQLite
        cursor = connection.execute(
            """INSERT INTO dead_letter_queue 
               (job_id, original_payload, failure_reason, sent_to_dlq_at, attempts, tenant_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (job_id, json.dumps(original_payload), failure_reason, now.isoformat(), attempts, tenant_id)
        )
        dlq_id = cursor.lastrowid
        
        connection.execute(
            "UPDATE job_queue SET status = ?, updated_at = ? WHERE job_id = ?",
            ("dead_lettered", now.isoformat(), job_id)
        )
        connection.commit()
        return dlq_id


def check_job_timeout(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    job_id: int,
    timeout_seconds: int
) -> bool:
    """Check if job processing has exceeded timeout. Returns True if timed out."""
    now = datetime.now(timezone.utc)
    timeout_at = datetime.fromtimestamp(now.timestamp() - timeout_seconds, tz=timezone.utc)
    
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """SELECT status, updated_at FROM job_queue WHERE job_id = %s""",
            (job_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        
        if row is None or row["status"] != "processing":
            return False
        
        # Check if updated_at is older than timeout
        updated_at = row["updated_at"]
        if updated_at < timeout_at:
            return True
    else:
        # SQLite
        cursor = connection.execute(
            "SELECT status, updated_at FROM job_queue WHERE job_id = ?",
            (job_id,)
        )
        row = cursor.fetchone()
        
        if row is None or row["status"] != "processing":
            return False
        
        updated_at = datetime.fromisoformat(row["updated_at"])
        if updated_at < timeout_at:
            return True
    
    return False


def enqueue_callback(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    job_id: int,
    callback_url: str,
    result_payload: dict,
    tenant_id: str | None = None
) -> int | None:
    """Enqueue callback for job completion. Returns callback ID."""
    now = datetime.now(timezone.utc)
    
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO callback_queue
               (job_id, callback_url, callback_status, result_payload, created_at, tenant_id)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING callback_id""",
            (job_id, callback_url, "pending", json.dumps(result_payload), now, tenant_id)
        )
        callback_id = cursor.fetchone()[0]
        connection.commit()
        cursor.close()
        return callback_id
    else:
        # SQLite
        cursor = connection.execute(
            """INSERT INTO callback_queue
               (job_id, callback_url, callback_status, result_payload, created_at, tenant_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (job_id, callback_url, "pending", json.dumps(result_payload), now.isoformat(), tenant_id)
        )
        callback_id = cursor.lastrowid
        connection.commit()
        return callback_id


def fetch_pending_callbacks(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    limit: int = 10
) -> list[dict]:
    """Fetch pending callbacks to send."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """SELECT callback_id, job_id, callback_url, result_payload, attempts, max_attempts
               FROM callback_queue
               WHERE callback_status = 'pending' AND (attempts < max_attempts)
               ORDER BY created_at ASC
               LIMIT %s""",
            (limit,)
        )
        rows = cursor.fetchall()
        cursor.close()
        
        return [dict(row) for row in rows]
    else:
        # SQLite
        cursor = connection.execute(
            """SELECT callback_id, job_id, callback_url, result_payload, attempts, max_attempts
               FROM callback_queue
               WHERE callback_status = 'pending' AND (attempts < max_attempts)
               ORDER BY created_at ASC
               LIMIT ?""",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

def fetch_callback_status_by_job_id(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    job_id: int
) -> list[dict]:
    """Fetch callback statuses for a specific job."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            "SELECT callback_id, callback_status, attempted_at, attempts, max_attempts FROM callback_queue WHERE job_id = %s",
            (job_id,)
        )
        rows = cursor.fetchall()
        cursor.close()
        
        return [dict(row) for row in rows]
    else:
        # SQLite
        cursor = connection.execute(
            "SELECT callback_id, callback_status, attempted_at, attempts, max_attempts FROM callback_queue WHERE job_id = ?",
            (job_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

def check_idempotency(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    idempotency_key: str
) -> dict | None:
    """Check if job with given idempotency key already exists. Returns job if exists."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            "SELECT job_id, status, result FROM job_queue WHERE idempotency_key = %s",
            (idempotency_key,)
        )
        row = cursor.fetchone()
        cursor.close()
        
        if row:
            return {"job_id": row["job_id"], "status": row["status"], "result": row["result"]}
    else:
        # SQLite
        cursor = connection.execute(
            "SELECT job_id, status, result FROM job_queue WHERE idempotency_key = ?",
            (idempotency_key,)
        )
        row = cursor.fetchone()
        
        if row:
            return {"job_id": row["job_id"], "status": row["status"], "result": row["result"]}
    
    return None


def store_callback_result(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    callback_id: int,
    status: str,
    error: str | None = None
) -> None:
    """Update callback status after send attempt."""
    now = datetime.now(timezone.utc)
    
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """UPDATE callback_queue 
               SET callback_status = %s, attempted_at = %s, attempts = attempts + 1
               WHERE callback_id = %s""",
            (status, now, callback_id)
        )
        connection.commit()
        cursor.close()
    else:
        # SQLite
        connection.execute(
            """UPDATE callback_queue 
               SET callback_status = ?, attempted_at = ?, attempts = attempts + 1
               WHERE callback_id = ?""",
            (status, now.isoformat(), callback_id)
        )
        connection.commit()

def fetch_dlq_jobs(connection: sqlite3.Connection | psycopg2.extensions.connection, limit: int = 10) -> list[dict]:
    """Fetch jobs from Dead Letter Queue."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """SELECT dlq_id, job_id, original_payload, failure_reason, sent_to_dlq_at, attempts, tenant_id
               FROM dead_letter_queue
               ORDER BY sent_to_dlq_at DESC
               LIMIT %s""",
            (limit,)
        )
        rows = cursor.fetchall()
        cursor.close()
        
        return [dict(row) for row in rows]
    else:
        # SQLite
        cursor = connection.execute(
            """SELECT dlq_id, job_id, original_payload, failure_reason, sent_to_dlq_at, attempts, tenant_id
               FROM dead_letter_queue
               ORDER BY sent_to_dlq_at DESC
               LIMIT ?""",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
