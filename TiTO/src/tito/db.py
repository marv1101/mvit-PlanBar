import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import pool as _pg_pool

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from .schema import extract_tenant_id

# Global PostgreSQL connection pool
_pg_pool: Any = None


def get_connection(
    database_url: str,
) -> sqlite3.Connection | psycopg2.extensions.connection:
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
    # Remove the scheme prefix for psycopg2
    database_url.replace("postgresql://", "").replace("postgres://", "")

    conn = psycopg2.connect(database_url)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

    # RealDictCursor: Alle Query-Ergebnisse kommen als dict-kompatible Rows
    # an, sodass sowohl row["col"] als auch dict(row) funktionieren.
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
            idempotency_key TEXT,
            timeout_at TEXT,
            tenant_id TEXT NOT NULL
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
    # Tenant-isolation indexes (B10): schnelle mandanten-scoped Filter auf allen Queue-Tabellen
    connection.execute("CREATE INDEX IF NOT EXISTS idx_job_queue_tenant ON job_queue(tenant_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_dead_letter_queue_tenant ON dead_letter_queue(tenant_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_callback_queue_tenant ON callback_queue(tenant_id)")
    # B6: Idempotenz mandanten-scoped — gleicher Key darf pro Tenant mehrfach existieren
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_job_queue_tenant_idempotency "
        "ON job_queue(tenant_id, idempotency_key) WHERE idempotency_key IS NOT NULL"
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
                idempotency_key TEXT,
                timeout_at TIMESTAMP WITH TIME ZONE,
                tenant_id TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dead_letter_queue (
                dlq_id SERIAL PRIMARY KEY,
                job_id SERIAL NOT NULL,
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
                job_id SERIAL NOT NULL,
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
        # Tenant-isolation indexes (B10): schnelle mandanten-scoped Filter auf allen Queue-Tabellen
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_queue_tenant ON job_queue(tenant_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dead_letter_queue_tenant ON dead_letter_queue(tenant_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_callback_queue_tenant ON callback_queue(tenant_id)")
        # B6: Idempotenz mandanten-scoped — gleicher Key darf pro Tenant mehrfach existieren.
        # Bestehende single-column UNIQUE-Constraint (aus alter Schema-Version) entfernen, falls vorhanden.
        try:
            cursor.execute("ALTER TABLE job_queue DROP CONSTRAINT IF EXISTS job_queue_idempotency_key_key")
        except psycopg2.Error:
            pass
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_job_queue_tenant_idempotency "
            "ON job_queue(tenant_id, idempotency_key) WHERE idempotency_key IS NOT NULL"
        )

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
    tenant_id: str | None = None,
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
    now = datetime.now(UTC)
    priority = int(payload.get("metadata", {}).get("priority", 0))

    # B10/B6: tenant_id Fallback aus Payload-Metadata, falls nicht explizit übergeben.
    # Stellt sicher, dass die NOT NULL-Spalte immer belegt wird (auch bei direkten enqueue_job-Aufrufen).
    if tenant_id is None:
        tenant_id = extract_tenant_id(payload.get("metadata"))
    if tenant_id is not None:
        tenant_id = str(tenant_id)

    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()

        # If idempotency_key provided, check for duplicate (B6: mandanten-scoped)
        if idempotency_key:
            cursor.execute(
                "SELECT job_id, status FROM job_queue WHERE idempotency_key = %s AND tenant_id = %s",
                (idempotency_key, tenant_id),
            )
            existing = cursor.fetchone()
            if existing:
                print(f"[DB] Duplicate job detected with idempotency_key: {idempotency_key} (tenant={tenant_id})")
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
                tenant_id,
            ),
        )
        job_id = cursor.fetchone()["job_id"]
        connection.commit()
        cursor.close()
        return job_id
    else:
        # SQLite
        if idempotency_key:
            cursor = connection.execute(
                "SELECT job_id, status FROM job_queue WHERE idempotency_key = ? AND tenant_id = ?",
                (idempotency_key, tenant_id),
            )
            existing = cursor.fetchone()
            if existing:
                print(f"[DB] Duplicate job detected with idempotency_key: {idempotency_key} (tenant={tenant_id})")
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
                tenant_id,
            ),
        )
        job_id = cursor.lastrowid
        try:
            connection.commit()
        except sqlite3.OperationalError as e:
            if "no transaction is active" in str(e):
                pass
            else:
                raise
        except Exception:
            if hasattr(connection, "commit"):
                connection.commit()
            else:
                raise
        return job_id


def fetch_job_by_id(
    connection: sqlite3.Connection | psycopg2.extensions.connection, job_id: int, tenant_id: str | None = None
) -> dict | None:
    """Fetch job details by job ID, optionally filtered by tenant."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        if tenant_id:
            cursor.execute("SELECT * FROM job_queue WHERE job_id = %s AND tenant_id = %s", (job_id, tenant_id))
        else:
            cursor.execute("SELECT * FROM job_queue WHERE job_id = %s", (job_id,))
        job = cursor.fetchone()
        cursor.close()

        if job is None:
            return None

        return dict(job)
    else:
        # SQLite
        if tenant_id:
            cursor = connection.execute(
                "SELECT * FROM job_queue WHERE job_id = ? AND tenant_id = ?", (job_id, tenant_id)
            )
        else:
            cursor = connection.execute("SELECT * FROM job_queue WHERE job_id = ?", (job_id,))
        job = cursor.fetchone()

        if job is None:
            return None

        return dict(job)


def fetch_job_status_by_id(
    connection: sqlite3.Connection | psycopg2.extensions.connection, job_id: int, tenant_id: str | None = None
) -> dict | None:
    """Fetch job status and details by job ID, optionally filtered by tenant."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        if tenant_id:
            cursor.execute(
                "SELECT job_id, status, result, attempts, max_retries, last_error FROM job_queue WHERE job_id = %s AND tenant_id = %s",
                (job_id, tenant_id),
            )
        else:
            cursor.execute(
                "SELECT job_id, status, result, attempts, max_retries, last_error FROM job_queue WHERE job_id = %s",
                (job_id,),
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
            "last_error": row["last_error"],
        }
    else:
        # SQLite
        if tenant_id:
            cursor = connection.execute(
                "SELECT job_id, status, result, attempts, max_retries, last_error FROM job_queue WHERE job_id = ? AND tenant_id = ?",
                (job_id, tenant_id),
            )
        else:
            cursor = connection.execute(
                "SELECT job_id, status, result, attempts, max_retries, last_error FROM job_queue WHERE job_id = ?",
                (job_id,),
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
            "last_error": row["last_error"],
        }


def fetch_next_job(connection: sqlite3.Connection | psycopg2.extensions.connection, queue_table: str) -> dict | None:
    """Fetch next queued job (FIFO with priority) WITHOUT claiming it (read-only inspection).

    For atomically claiming a job (status -> 'processing') use claim_next_job() instead (F1).
    Handles both SQLite and PostgreSQL."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            f"""SELECT * FROM {queue_table}
               WHERE status = 'queued' AND (scheduled_for IS NULL OR scheduled_for <= NOW())
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


def claim_next_job(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    queue_table: str,
    lease_seconds: int = 600,
    max_candidates: int = 10,
) -> dict | None:
    """F1: Atomar den nächsten fälligen Job claimen (status -> 'processing', attempts +1, timeout_at gesetzt).

    Postgres: SELECT ... FOR UPDATE SKIP LOCKED + bedingtes UPDATE in EINER Anweisung
    (wirkt auch im AUTOCOMMIT-Modus der Verbindung, da die Anweisung selbst atomar ist).
    SQLite: Kandidaten-IDs selektieren, dann bedingtes UPDATE mit WHERE status='queued';
    bei rowcount 0 wird der nächste Kandidat versucht (Loop).

    Gibt das Payload (mit '_db_job_id') zurück oder None, wenn kein Job verfügbar ist."""
    now = datetime.now(UTC)
    timeout_at = now + timedelta(seconds=lease_seconds)

    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            f"""UPDATE {queue_table}
                SET status = 'processing', attempts = attempts + 1, timeout_at = %s, updated_at = %s
                WHERE job_id = (
                    SELECT job_id FROM {queue_table}
                    WHERE status = 'queued' AND (scheduled_for IS NULL OR scheduled_for <= NOW())
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                AND status = 'queued'
                RETURNING job_id, payload""",
            (timeout_at, now),
        )
        row = cursor.fetchone()
        connection.commit()
        cursor.close()

        if row is None:
            return None

        payload = row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"])
        payload["_db_job_id"] = row["job_id"]
        return payload
    else:
        # SQLite: Kandidaten selektieren, dann bedingt (guarded) claimen
        cursor = connection.execute(
            f"""SELECT job_id, payload FROM {queue_table}
                WHERE status = 'queued' AND (scheduled_for IS NULL OR scheduled_for <= ?)
                ORDER BY priority DESC, created_at ASC LIMIT ?""",
            (now.isoformat(), max_candidates),
        )
        rows = cursor.fetchall()

        for row in rows:
            if mark_job_processing(connection, row["job_id"], lease_seconds=lease_seconds):
                payload = json.loads(row["payload"])
                payload["_db_job_id"] = row["job_id"]
                return payload
        return None


def mark_job_processing(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    job_id: int,
    lease_seconds: int = 600,
) -> bool:
    """F1/F2: Job atomar als 'processing' claimen.

    Der UPDATE ist mit WHERE status='queued' abgesichert: konkurrierende Worker können
    denselben Job nicht doppelt claimen. Gleichzeitig wird der Lease (timeout_at = now +
    lease_seconds) gesetzt, damit hängengebliebene Jobs wiederentdeckt werden können.

    Returns:
        True, wenn der Claim erfolgreich war (Job war 'queued'); False sonst.
    """
    now = datetime.now(UTC)
    timeout_at = now + timedelta(seconds=lease_seconds)

    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """UPDATE job_queue SET status = %s, updated_at = %s, attempts = attempts + 1, timeout_at = %s
               WHERE job_id = %s AND status = 'queued'""",
            ("processing", now, timeout_at, job_id),
        )
        claimed = cursor.rowcount > 0
        connection.commit()
        cursor.close()
        return claimed
    else:
        # SQLite
        cursor = connection.execute(
            """UPDATE job_queue SET status = ?, updated_at = ?, attempts = attempts + 1, timeout_at = ?
               WHERE job_id = ? AND status = 'queued'""",
            ("processing", now.isoformat(), timeout_at.isoformat(), job_id),
        )
        claimed = cursor.rowcount > 0
        connection.commit()
        return claimed


def update_job(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    job_id: int,
    status: str,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    """Update job status, result and error information."""
    now = datetime.now(UTC)

    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """UPDATE job_queue SET status = %s, result = %s, last_error = %s, updated_at = %s WHERE job_id = %s""",
            (status, json.dumps(result) if result else None, error, now, job_id),
        )
        connection.commit()
        cursor.close()
    else:
        # SQLite
        connection.execute(
            "UPDATE job_queue SET status = ?, result = ?, last_error = ?, updated_at = ? WHERE job_id = ?",
            (
                status,
                json.dumps(result) if result else None,
                error,
                now.isoformat(),
                job_id,
            ),
        )
        connection.commit()


def store_result(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    job_id: int,
    result: dict,
) -> None:
    """Store job result and mark as completed."""
    now = datetime.now(UTC)

    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """UPDATE job_queue SET status = %s, result = %s, updated_at = %s WHERE job_id = %s""",
            ("completed", json.dumps(result), now, job_id),
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


def count_jobs(
    connection: sqlite3.Connection | psycopg2.extensions.connection, queue_table: str, tenant_id: str | None = None
) -> int:
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        if tenant_id:
            cursor.execute(f"SELECT COUNT(1) AS count FROM {queue_table} WHERE tenant_id = %s", (tenant_id,))
        else:
            cursor.execute(f"SELECT COUNT(1) AS count FROM {queue_table}")
        row = cursor.fetchone()
        cursor.close()
        return int(row["count"])
    else:
        if tenant_id:
            cursor = connection.execute(
                f"SELECT COUNT(1) AS count FROM {queue_table} WHERE tenant_id = ?", (tenant_id,)
            )
        else:
            cursor = connection.execute(f"SELECT COUNT(1) AS count FROM {queue_table}")
        row = cursor.fetchone()
        return int(row["count"])


def list_jobs_by_tenant(
    connection: sqlite3.Connection | psycopg2.extensions.connection, queue_table: str, tenant_id: str
) -> list[dict]:
    """List all jobs for a specific tenant."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            f"SELECT job_id, status, priority, created_at, updated_at FROM {queue_table} WHERE tenant_id = %s ORDER BY created_at DESC",
            (tenant_id,),
        )
        jobs = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        return jobs
    else:
        cursor = connection.execute(
            f"SELECT job_id, status, priority, created_at, updated_at FROM {queue_table} WHERE tenant_id = ? ORDER BY created_at DESC",
            (tenant_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def register_worker(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    worker_id: str,
    ip: str,
    cpu_usage: float,
    ram_usage: float,
) -> None:
    now = datetime.now(UTC)
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO workers (worker_id, ip, registered_at, last_heartbeat, cpu_usage, ram_usage, active_jobs) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (worker_id) DO UPDATE SET
               ip = EXCLUDED.ip,
               registered_at = EXCLUDED.registered_at,
               last_heartbeat = EXCLUDED.last_heartbeat,
               cpu_usage = EXCLUDED.cpu_usage,
               ram_usage = EXCLUDED.ram_usage,
               active_jobs = EXCLUDED.active_jobs""",
            (worker_id, ip, now, now, cpu_usage, ram_usage, 0),
        )
        connection.commit()
        cursor.close()
    else:
        now_iso = now.isoformat()
        connection.execute(
            "INSERT OR REPLACE INTO workers (worker_id, ip, registered_at, last_heartbeat, cpu_usage, ram_usage, active_jobs) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (worker_id, ip, now_iso, now_iso, cpu_usage, ram_usage, 0),
        )
        connection.commit()


def update_worker_heartbeat(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    worker_id: str,
    cpu_usage: float,
    ram_usage: float,
    active_jobs: int,
) -> None:
    now = datetime.now(UTC)
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE workers SET last_heartbeat = %s, cpu_usage = %s, ram_usage = %s, active_jobs = %s WHERE worker_id = %s",
            (now, cpu_usage, ram_usage, active_jobs, worker_id),
        )
        connection.commit()
        cursor.close()
    else:
        now_iso = now.isoformat()
        connection.execute(
            "UPDATE workers SET last_heartbeat = ?, cpu_usage = ?, ram_usage = ?, active_jobs = ? WHERE worker_id = ?",
            (now_iso, cpu_usage, ram_usage, active_jobs, worker_id),
        )
        connection.commit()


def get_workers(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
) -> list[dict]:
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM workers ORDER BY registered_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]
    else:
        cursor = connection.execute("SELECT * FROM workers ORDER BY registered_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def count_workers(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
) -> int:
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(1) AS count FROM workers")
        row = cursor.fetchone()
        cursor.close()
        return int(row["count"])
    else:
        cursor = connection.execute("SELECT COUNT(1) AS count FROM workers")
        row = cursor.fetchone()
        return int(row["count"])


def deregister_worker(connection: sqlite3.Connection | psycopg2.extensions.connection, worker_id: str) -> None:
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute("DELETE FROM workers WHERE worker_id = %s", (worker_id,))
        connection.commit()
        cursor.close()
    else:
        connection.execute("DELETE FROM workers WHERE worker_id = ?", (worker_id,))
        connection.commit()


def cleanup_inactive_workers(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    timeout_seconds: int = 300,
) -> int:
    """Remove workers that haven't sent a heartbeat within the timeout period."""
    cutoff_time = datetime.now(UTC) - timedelta(seconds=timeout_seconds)
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute("DELETE FROM workers WHERE last_heartbeat < %s", (cutoff_time,))
        deleted_count = cursor.rowcount
        connection.commit()
        cursor.close()
        return deleted_count
    else:
        cutoff_iso = cutoff_time.isoformat()
        cursor = connection.execute("DELETE FROM workers WHERE last_heartbeat < ?", (cutoff_iso,))
        deleted_count = cursor.rowcount
        connection.commit()
        return deleted_count


def mark_job_failed_with_retry(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    job_id: int,
    error: str,
    base_delay: int = 5,
) -> bool:
    """
    Mark job as failed and schedule retry with exponential backoff.
    Returns True if job will be retried, False if max retries exceeded (move to DLQ).

    Backoff calculation: base_delay * (2 ^ attempts) seconds
    """
    now = datetime.now(UTC)

    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()

        # Get current attempt count and max_retries
        cursor.execute("SELECT attempts, max_retries FROM job_queue WHERE job_id = %s", (job_id,))
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
                ("failed", now, error, now, job_id),
            )
            connection.commit()
            cursor.close()
            return False

        # Schedule retry with exponential backoff
        backoff_seconds = base_delay * (2**attempts)
        scheduled_for = datetime.fromtimestamp(now.timestamp() + backoff_seconds, tz=UTC)

        cursor = connection.cursor()
        cursor.execute(
            """UPDATE job_queue SET status = %s, scheduled_for = %s, last_error = %s, updated_at = %s 
               WHERE job_id = %s""",
            ("queued", scheduled_for, error, now, job_id),
        )
        connection.commit()
        cursor.close()
        return True
    else:
        # SQLite
        cursor = connection.execute("SELECT attempts, max_retries FROM job_queue WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()

        if row is None:
            return False

        attempts = row["attempts"]
        max_retries = row["max_retries"] or 3

        if attempts >= max_retries:
            connection.execute(
                "UPDATE job_queue SET status = ?, failed_at = ?, last_error = ?, updated_at = ? WHERE job_id = ?",
                ("failed", now.isoformat(), error, now.isoformat(), job_id),
            )
            connection.commit()
            return False

        backoff_seconds = base_delay * (2**attempts)
        scheduled_for = datetime.fromtimestamp(now.timestamp() + backoff_seconds, tz=UTC)

        connection.execute(
            "UPDATE job_queue SET status = ?, scheduled_for = ?, last_error = ?, updated_at = ? WHERE job_id = ?",
            ("queued", scheduled_for.isoformat(), error, now.isoformat(), job_id),
        )
        connection.commit()
        return True


def move_job_to_dlq(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    job_id: int,
    original_payload: dict,
    failure_reason: str,
    attempts: int,
    tenant_id: str | None = None,
) -> int | None:
    """Move permanently failed job to Dead Letter Queue. Returns DLQ ID."""
    now = datetime.now(UTC)

    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO dead_letter_queue 
               (job_id, original_payload, failure_reason, sent_to_dlq_at, attempts, tenant_id)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING dlq_id""",
            (
                job_id,
                json.dumps(original_payload),
                failure_reason,
                now,
                attempts,
                tenant_id,
            ),
        )
        dlq_id = cursor.fetchone()["dlq_id"]

        # Mark job as dead_lettered
        cursor.execute(
            "UPDATE job_queue SET status = %s, updated_at = %s WHERE job_id = %s",
            ("dead_lettered", now, job_id),
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
            (
                job_id,
                json.dumps(original_payload),
                failure_reason,
                now.isoformat(),
                attempts,
                tenant_id,
            ),
        )
        dlq_id = cursor.lastrowid

        connection.execute(
            "UPDATE job_queue SET status = ?, updated_at = ? WHERE job_id = ?",
            ("dead_lettered", now.isoformat(), job_id),
        )
        connection.commit()
        return dlq_id


def check_job_timeout(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    job_id: int,
) -> bool:
    """F2: Prüft anhand des Lease (timeout_at), ob ein 'processing'-Job feststeckt.

    Returns True, wenn der Job im Status 'processing' ist und sein timeout_at in der
    Vergangenheit liegt (z.B. nach einem Worker-Crash)."""
    now = datetime.now(UTC)

    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute("SELECT status, timeout_at FROM job_queue WHERE job_id = %s", (job_id,))
        row = cursor.fetchone()
        cursor.close()

        if row is None or row["status"] != "processing" or row["timeout_at"] is None:
            return False

        return row["timeout_at"] < now
    else:
        # SQLite
        cursor = connection.execute("SELECT status, timeout_at FROM job_queue WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()

        if row is None or row["status"] != "processing" or row["timeout_at"] is None:
            return False

        return datetime.fromisoformat(row["timeout_at"]) < now


def reclaim_timed_out_jobs(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    queue_table: str = "job_queue",
) -> list[dict]:
    """F2: Festhängende 'processing'-Jobs mit abgelaufenem Lease wiederentdecken.

    Wird regelmäßig vom Worker-Loop und vom Cleanup-Thread der API aufgerufen.
    - attempts < max_retries: Job zurück auf 'queued' (inkl. last_error-Hinweis).
    - attempts >= max_retries: terminal - Job in die DLQ verschieben und Fehler-Callback
      mit FAILED-Payload enqueueen (F3), sofern eine callback_url hinterlegt ist.

    Returns Liste der behandelten Jobs als {"job_id": ..., "action": "requeued"|"dead_lettered"}."""
    now = datetime.now(UTC)

    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            f"""SELECT job_id, payload, attempts, max_retries, callback_url, tenant_id FROM {queue_table}
                WHERE status = 'processing' AND timeout_at IS NOT NULL AND timeout_at < %s
                ORDER BY created_at ASC""",
            (now,),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        cursor.close()
    else:
        # SQLite
        cursor = connection.execute(
            f"""SELECT job_id, payload, attempts, max_retries, callback_url, tenant_id FROM {queue_table}
                WHERE status = 'processing' AND timeout_at IS NOT NULL AND timeout_at < ?
                ORDER BY created_at ASC""",
            (now.isoformat(),),
        )
        rows = [dict(row) for row in cursor.fetchall()]

    reclaimed: list[dict] = []

    for row in rows:
        job_id = row["job_id"]
        attempts = row["attempts"] or 0
        max_retries = row["max_retries"] or 3
        reason = f"Processing lease expired (worker crashed?) after {attempts} attempt(s)"
        payload = row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"])

        if attempts < max_retries:
            # Zurück in die Queue - guarded, damit konkurrierende Sweeper nicht doppelt reagieren
            if isinstance(connection, psycopg2.extensions.connection):
                cursor = connection.cursor()
                cursor.execute(
                    """UPDATE job_queue SET status = %s, timeout_at = NULL, last_error = %s, updated_at = %s
                       WHERE job_id = %s AND status = 'processing'""",
                    ("queued", reason, now, job_id),
                )
                requeued = cursor.rowcount > 0
                connection.commit()
                cursor.close()
            else:
                cursor = connection.execute(
                    """UPDATE job_queue SET status = ?, timeout_at = NULL, last_error = ?, updated_at = ?
                       WHERE job_id = ? AND status = 'processing'""",
                    ("queued", reason, now.isoformat(), job_id),
                )
                requeued = cursor.rowcount > 0
                connection.commit()

            if requeued:
                reclaimed.append({"job_id": job_id, "action": "requeued"})
        else:
            # Terminal: Versuche erschöpft -> 'failed' setzen (guarded), dann DLQ + Fehler-Callback (F3)
            if isinstance(connection, psycopg2.extensions.connection):
                cursor = connection.cursor()
                cursor.execute(
                    """UPDATE job_queue SET status = %s, failed_at = %s, last_error = %s, timeout_at = NULL,
                       updated_at = %s WHERE job_id = %s AND status = 'processing'""",
                    ("failed", now, reason, now, job_id),
                )
                failed = cursor.rowcount > 0
                connection.commit()
                cursor.close()
            else:
                cursor = connection.execute(
                    """UPDATE job_queue SET status = ?, failed_at = ?, last_error = ?, timeout_at = NULL,
                       updated_at = ? WHERE job_id = ? AND status = 'processing'""",
                    ("failed", now.isoformat(), reason, now.isoformat(), job_id),
                )
                failed = cursor.rowcount > 0
                connection.commit()

            if not failed:
                continue

            move_job_to_dlq(
                connection,
                job_id,
                payload,
                reason,
                attempts=attempts,
                tenant_id=row["tenant_id"],
            )

            if row["callback_url"]:
                enqueue_callback(
                    connection,
                    job_id,
                    row["callback_url"],
                    {"job_id": job_id, "status": "FAILED", "error": reason, "attempts": attempts},
                    tenant_id=row["tenant_id"],
                )

            reclaimed.append({"job_id": job_id, "action": "dead_lettered"})

    return reclaimed


def retry_job(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    job_id: int,
) -> bool:
    """F6: Manual-Retry eines endgültig fehlgeschlagenen Jobs.

    Setzt attempts=0, last_error=NULL, timeout_at=NULL und scheduled_for=NULL, damit der
    Job nach dem Retry wieder den vollen Retry-Rahmen hat (statt sofort wieder in die DLQ
    zu wandern). Gibt True zurück, wenn der Job re-queued wurde."""
    now = datetime.now(UTC)

    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """UPDATE job_queue SET status = 'queued', attempts = 0, last_error = NULL, timeout_at = NULL,
               scheduled_for = NULL, failed_at = NULL, updated_at = %s
               WHERE job_id = %s AND status IN ('failed', 'dead_lettered')""",
            (now, job_id),
        )
        retried = cursor.rowcount > 0
        connection.commit()
        cursor.close()
        return retried
    else:
        # SQLite
        cursor = connection.execute(
            """UPDATE job_queue SET status = 'queued', attempts = 0, last_error = NULL, timeout_at = NULL,
               scheduled_for = NULL, failed_at = NULL, updated_at = ?
               WHERE job_id = ? AND status IN ('failed', 'dead_lettered')""",
            (now.isoformat(), job_id),
        )
        retried = cursor.rowcount > 0
        connection.commit()
        return retried


def enqueue_callback(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    job_id: int,
    callback_url: str,
    result_payload: dict,
    tenant_id: str | None = None,
) -> int | None:
    """Enqueue callback for job completion. Returns callback ID."""
    now = datetime.now(UTC)

    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO callback_queue
               (job_id, callback_url, callback_status, result_payload, created_at, tenant_id)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING callback_id""",
            (
                job_id,
                callback_url,
                "pending",
                json.dumps(result_payload),
                now,
                tenant_id,
            ),
        )
        callback_id = cursor.fetchone()["callback_id"]
        connection.commit()
        cursor.close()
        return callback_id
    else:
        # SQLite
        cursor = connection.execute(
            """INSERT INTO callback_queue
               (job_id, callback_url, callback_status, result_payload, created_at, tenant_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                job_id,
                callback_url,
                "pending",
                json.dumps(result_payload),
                now.isoformat(),
                tenant_id,
            ),
        )
        callback_id = cursor.lastrowid
        connection.commit()
        return callback_id


def fetch_pending_callbacks(
    connection: sqlite3.Connection | psycopg2.extensions.connection, limit: int = 10, tenant_id: str | None = None
) -> list[dict]:
    """Fetch pending callbacks to send, optionally filtered by tenant (B4)."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        if tenant_id:
            cursor.execute(
                """SELECT callback_id, job_id, callback_url, result_payload, attempts, max_attempts
                   FROM callback_queue
                   WHERE callback_status = 'pending' AND (attempts < max_attempts) AND tenant_id = %s
                   ORDER BY created_at ASC
                   LIMIT %s""",
                (tenant_id, limit),
            )
        else:
            cursor.execute(
                """SELECT callback_id, job_id, callback_url, result_payload, attempts, max_attempts
                   FROM callback_queue
                   WHERE callback_status = 'pending' AND (attempts < max_attempts)
                   ORDER BY created_at ASC
                   LIMIT %s""",
                (limit,),
            )
        rows = cursor.fetchall()
        cursor.close()

        return [dict(row) for row in rows]
    else:
        # SQLite
        if tenant_id:
            cursor = connection.execute(
                """SELECT callback_id, job_id, callback_url, result_payload, attempts, max_attempts
                   FROM callback_queue
                   WHERE callback_status = 'pending' AND (attempts < max_attempts) AND tenant_id = ?
                   ORDER BY created_at ASC
                   LIMIT ?""",
                (tenant_id, limit),
            )
        else:
            cursor = connection.execute(
                """SELECT callback_id, job_id, callback_url, result_payload, attempts, max_attempts
                   FROM callback_queue
                   WHERE callback_status = 'pending' AND (attempts < max_attempts)
                   ORDER BY created_at ASC
                   LIMIT ?""",
                (limit,),
            )
        return [dict(row) for row in cursor.fetchall()]


def fetch_callback_count_grouped_by_status(
    connection: sqlite3.Connection | psycopg2.extensions.connection, tenant_id: str | None = None
) -> dict:
    """Fetch count of callbacks grouped by status, optionally filtered by tenant (B5)."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        if tenant_id:
            cursor.execute(
                "SELECT callback_status, COUNT(*) as count FROM callback_queue WHERE tenant_id = %s GROUP BY callback_status",
                (tenant_id,),
            )
        else:
            cursor.execute("SELECT callback_status, COUNT(*) as count FROM callback_queue GROUP BY callback_status")
        rows = cursor.fetchall()
        cursor.close()

        return {row["callback_status"]: row["count"] for row in rows}
    else:
        # SQLite
        if tenant_id:
            cursor = connection.execute(
                "SELECT callback_status, COUNT(*) as count FROM callback_queue WHERE tenant_id = ? GROUP BY callback_status",
                (tenant_id,),
            )
        else:
            cursor = connection.execute(
                "SELECT callback_status, COUNT(*) as count FROM callback_queue GROUP BY callback_status"
            )
        return {row["callback_status"]: row["count"] for row in cursor.fetchall()}


def fetch_callback_status_by_job_id(
    connection: sqlite3.Connection | psycopg2.extensions.connection, job_id: int, tenant_id: str | None = None
) -> list[dict]:
    """Fetch callback statuses for a specific job, optionally filtered by tenant (B8)."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        if tenant_id:
            cursor.execute(
                "SELECT callback_id, callback_status, attempted_at, attempts, max_attempts FROM callback_queue WHERE job_id = %s AND tenant_id = %s",
                (job_id, tenant_id),
            )
        else:
            cursor.execute(
                "SELECT callback_id, callback_status, attempted_at, attempts, max_attempts FROM callback_queue WHERE job_id = %s",
                (job_id,),
            )
        rows = cursor.fetchall()
        cursor.close()

        return [dict(row) for row in rows]
    else:
        # SQLite
        if tenant_id:
            cursor = connection.execute(
                "SELECT callback_id, callback_status, attempted_at, attempts, max_attempts FROM callback_queue WHERE job_id = ? AND tenant_id = ?",
                (job_id, tenant_id),
            )
        else:
            cursor = connection.execute(
                "SELECT callback_id, callback_status, attempted_at, attempts, max_attempts FROM callback_queue WHERE job_id = ?",
                (job_id,),
            )
        return [dict(row) for row in cursor.fetchall()]


def check_idempotency(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    idempotency_key: str,
    tenant_id: str | None = None,
) -> dict | None:
    """Check if job with given idempotency key already exists. Returns job if exists (B6: mandanten-scoped)."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        if tenant_id:
            cursor.execute(
                "SELECT job_id, status, result FROM job_queue WHERE idempotency_key = %s AND tenant_id = %s",
                (idempotency_key, tenant_id),
            )
        else:
            cursor.execute(
                "SELECT job_id, status, result FROM job_queue WHERE idempotency_key = %s",
                (idempotency_key,),
            )
        row = cursor.fetchone()
        cursor.close()

        if row:
            return {
                "job_id": row["job_id"],
                "status": row["status"],
                "result": row["result"],
            }
    else:
        # SQLite
        if tenant_id:
            cursor = connection.execute(
                "SELECT job_id, status, result FROM job_queue WHERE idempotency_key = ? AND tenant_id = ?",
                (idempotency_key, tenant_id),
            )
        else:
            cursor = connection.execute(
                "SELECT job_id, status, result FROM job_queue WHERE idempotency_key = ?",
                (idempotency_key,),
            )
        row = cursor.fetchone()

        if row:
            return {
                "job_id": row["job_id"],
                "status": row["status"],
                "result": row["result"],
            }

    return None


def claim_callback(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    callback_id: int,
) -> bool:
    """F5: Atomaren Claim eines pending Callbacks VOR dem Versand.

    UPDATE callback_queue SET status='sending', attempts=attempts+1 WHERE id=? AND status='pending':
    konkurrierende Worker können denselben Callback nicht doppelt versenden.

    Returns:
        True, wenn der Claim erfolgreich war; False, wenn der Callback nicht (mehr) pending ist."""
    now = datetime.now(UTC)

    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """UPDATE callback_queue SET callback_status = 'sending', attempts = attempts + 1, attempted_at = %s
               WHERE callback_id = %s AND callback_status = 'pending'""",
            (now, callback_id),
        )
        claimed = cursor.rowcount > 0
        connection.commit()
        cursor.close()
        return claimed
    else:
        # SQLite
        cursor = connection.execute(
            """UPDATE callback_queue SET callback_status = 'sending', attempts = attempts + 1, attempted_at = ?
               WHERE callback_id = ? AND callback_status = 'pending'""",
            (now.isoformat(), callback_id),
        )
        claimed = cursor.rowcount > 0
        connection.commit()
        return claimed


def requeue_stale_sending_callbacks(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    stale_seconds: int = 60,
) -> int:
    """F5: Callbacks, die im Status 'sending' hängen (Worker-Crash während des Versands),
    zurück auf 'pending' setzen, damit sie erneut versendet werden.

    Returns Anzahl der re-queued Callbacks."""
    cutoff = datetime.now(UTC) - timedelta(seconds=stale_seconds)

    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """UPDATE callback_queue SET callback_status = 'pending'
               WHERE callback_status = 'sending' AND attempted_at IS NOT NULL AND attempted_at < %s""",
            (cutoff,),
        )
        count = cursor.rowcount
        connection.commit()
        cursor.close()
        return count
    else:
        # SQLite
        cursor = connection.execute(
            """UPDATE callback_queue SET callback_status = 'pending'
               WHERE callback_status = 'sending' AND attempted_at IS NOT NULL AND attempted_at < ?""",
            (cutoff.isoformat(),),
        )
        count = cursor.rowcount
        connection.commit()
        return count


def store_callback_result(
    connection: sqlite3.Connection | psycopg2.extensions.connection,
    callback_id: int,
    status: str,
    error: str | None = None,
) -> None:
    """Update callback status after send attempt.

    Hinweis (F5): attempts wird bereits beim atomaren Claim (claim_callback) inkrementiert
    und hier bewusst NICHT nochmals erhöht."""
    now = datetime.now(UTC)

    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        cursor.execute(
            """UPDATE callback_queue
               SET callback_status = %s, attempted_at = %s
               WHERE callback_id = %s""",
            (status, now, callback_id),
        )
        connection.commit()
        cursor.close()
    else:
        # SQLite
        connection.execute(
            """UPDATE callback_queue
               SET callback_status = ?, attempted_at = ?
               WHERE callback_id = ?""",
            (status, now.isoformat(), callback_id),
        )
        connection.commit()


def fetch_dlq_count(
    connection: sqlite3.Connection | psycopg2.extensions.connection, tenant_id: str | None = None
) -> int:
    """Fetch count of jobs in Dead Letter Queue, optionally filtered by tenant (B5)."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        if tenant_id:
            cursor.execute("SELECT COUNT(*) as count FROM dead_letter_queue WHERE tenant_id = %s", (tenant_id,))
        else:
            cursor.execute("SELECT COUNT(*) as count FROM dead_letter_queue")
        row = cursor.fetchone()
        cursor.close()
        return row["count"]
    else:
        # SQLite
        if tenant_id:
            cursor = connection.execute(
                "SELECT COUNT(*) as count FROM dead_letter_queue WHERE tenant_id = ?", (tenant_id,)
            )
        else:
            cursor = connection.execute("SELECT COUNT(*) as count FROM dead_letter_queue")
        row = cursor.fetchone()
        return int(row["count"])


def fetch_dlq_jobs(
    connection: sqlite3.Connection | psycopg2.extensions.connection, limit: int = 10, tenant_id: str | None = None
) -> list[dict]:
    """Fetch jobs from Dead Letter Queue, optionally filtered by tenant."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        if tenant_id:
            cursor.execute(
                """SELECT dlq_id, job_id, original_payload, failure_reason, sent_to_dlq_at, attempts, tenant_id
                   FROM dead_letter_queue
                   WHERE tenant_id = %s
                   ORDER BY sent_to_dlq_at DESC
                   LIMIT %s""",
                (tenant_id, limit),
            )
        else:
            cursor.execute(
                """SELECT dlq_id, job_id, original_payload, failure_reason, sent_to_dlq_at, attempts, tenant_id
                   FROM dead_letter_queue
                   ORDER BY sent_to_dlq_at DESC
                   LIMIT %s""",
                (limit,),
            )
        rows = cursor.fetchall()
        cursor.close()

        return [dict(row) for row in rows]
    else:
        # SQLite
        if tenant_id:
            cursor = connection.execute(
                """SELECT dlq_id, job_id, original_payload, failure_reason, sent_to_dlq_at, attempts, tenant_id
                   FROM dead_letter_queue
                   WHERE tenant_id = ?
                   ORDER BY sent_to_dlq_at DESC
                   LIMIT ?""",
                (tenant_id, limit),
            )
        else:
            cursor = connection.execute(
                """SELECT dlq_id, job_id, original_payload, failure_reason, sent_to_dlq_at, attempts, tenant_id
                   FROM dead_letter_queue
                   ORDER BY sent_to_dlq_at DESC
                   LIMIT ?""",
                (limit,),
            )
        return [dict(row) for row in cursor.fetchall()]


def fetch_jobs_grouped_by_status(
    connection: sqlite3.Connection | psycopg2.extensions.connection, queue_table: str, tenant_id: str | None = None
) -> dict:
    """Fetch job counts grouped by status, optionally filtered by tenant (B5)."""
    if isinstance(connection, psycopg2.extensions.connection):
        cursor = connection.cursor()
        if tenant_id:
            cursor.execute(
                f"SELECT status, COUNT(*) as count FROM {queue_table} WHERE tenant_id = %s GROUP BY status",
                (tenant_id,),
            )
        else:
            cursor.execute(f"SELECT status, COUNT(*) as count FROM {queue_table} GROUP BY status")
        rows = cursor.fetchall()
        cursor.close()

        return {row["status"]: row["count"] for row in rows}
    else:
        # SQLite
        if tenant_id:
            cursor = connection.execute(
                f"SELECT status, COUNT(*) as count FROM {queue_table} WHERE tenant_id = ? GROUP BY status",
                (tenant_id,),
            )
        else:
            cursor = connection.execute(f"SELECT status, COUNT(*) as count FROM {queue_table} GROUP BY status")
        return {row["status"]: row["count"] for row in cursor.fetchall()}
