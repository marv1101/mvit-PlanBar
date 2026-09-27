import json
import sqlite3
from datetime import datetime
from typing import Any

from .db import (
    count_jobs,
    fetch_callback_count_grouped_by_status,
    fetch_dlq_count,
    fetch_jobs_grouped_by_status,
    get_workers,
)


def _parse_result(result: Any) -> dict | None:
    if result is None:
        return None
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return None
    if isinstance(result, dict):
        return result
    return None


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _fetch_job_rows(connection: sqlite3.Connection | Any, queue_table: str, tenant_id: str | None = None) -> list[dict]:
    query = f"SELECT status, result, created_at, updated_at FROM {queue_table}"
    params: tuple = ()
    if tenant_id:
        query += " WHERE tenant_id = ?"
        params = (tenant_id,)
    if isinstance(connection, sqlite3.Connection):
        cursor = connection.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
    else:
        cursor = connection.cursor()
        if tenant_id:
            cursor.execute(
                f"SELECT status, result, created_at, updated_at FROM {queue_table} WHERE tenant_id = %s",
                (tenant_id,),
            )
        else:
            cursor.execute(query)
        rows = [dict(row) for row in cursor.fetchall()]
        cursor.close()
    return rows


def _compute_duration_metrics(
    connection: sqlite3.Connection | Any, queue_table: str, tenant_id: str | None = None
) -> dict:
    durations = []
    for row in _fetch_job_rows(connection, queue_table, tenant_id):
        created_at = _parse_timestamp(row.get("created_at"))
        updated_at = _parse_timestamp(row.get("updated_at"))
        if created_at is None or updated_at is None:
            continue
        durations.append((updated_at - created_at).total_seconds())

    if not durations:
        return {
            "average_job_duration_seconds": 0.0,
            "max_job_duration_seconds": 0.0,
            "median_job_duration_seconds": 0.0,
        }

    durations.sort()
    count = len(durations)
    median = durations[count // 2] if count % 2 == 1 else (durations[count // 2 - 1] + durations[count // 2]) / 2
    return {
        "average_job_duration_seconds": round(sum(durations) / count, 2),
        "max_job_duration_seconds": round(max(durations), 2),
        "median_job_duration_seconds": round(median, 2),
    }


def _compute_timeout_metrics(
    connection: sqlite3.Connection | Any, queue_table: str, timeout_seconds: int | None, tenant_id: str | None = None
) -> dict:
    if timeout_seconds is None:
        return {"solver_timeout_count": 0, "solver_timeout_rate": 0.0}

    timeout_count = 0
    checked = 0
    for row in _fetch_job_rows(connection, queue_table, tenant_id):
        result = _parse_result(row.get("result"))
        if not isinstance(result, dict):
            continue
        metadata = result.get("metadata", {})
        solve_time = metadata.get("solveTimeSeconds")
        if isinstance(solve_time, (int, float)):
            checked += 1
            if solve_time >= timeout_seconds:
                timeout_count += 1

    return {
        "solver_timeout_count": timeout_count,
        "solver_timeout_rate": round((timeout_count / checked) * 100, 2) if checked else 0.0,
    }


def _compute_error_rate(job_status_counts: dict) -> float:
    processed = sum(job_status_counts.get(status, 0) for status in ("completed", "failed", "dead_lettered"))
    failures = job_status_counts.get("failed", 0) + job_status_counts.get("dead_lettered", 0)
    if processed == 0:
        return 0.0
    return round((failures / processed) * 100, 2)


def get_metrics(
    connection: sqlite3.Connection | Any,
    queue_table: str,
    timeout_seconds: int | None = None,
    tenant_id: str | None = None,
) -> dict:
    """Gibt aktuelle Monitoring-Daten zurück, optional mandanten-scoped (B5)."""
    workers = get_workers(connection) if not tenant_id else []
    job_status_counts = fetch_jobs_grouped_by_status(connection, queue_table, tenant_id)
    callback_counts = fetch_callback_count_grouped_by_status(connection, tenant_id)
    dlq_count = fetch_dlq_count(connection, tenant_id)
    duration_metrics = _compute_duration_metrics(connection, queue_table, tenant_id)
    timeout_metrics = _compute_timeout_metrics(connection, queue_table, timeout_seconds, tenant_id)
    error_rate = _compute_error_rate(job_status_counts)

    return {
        "queue_length": count_jobs(connection, queue_table, tenant_id),
        "active_workers": len(workers),
        "worker_count": len(workers),
        "workers": workers,
        "job_status_counts": job_status_counts,
        "dead_letter_queue_size": dlq_count,
        "callback_counts": callback_counts,
        "error_rate": error_rate,
        **duration_metrics,
        **timeout_metrics,
    }


def export_prometheus(
    connection: sqlite3.Connection | Any,
    queue_table: str,
    timeout_seconds: int | None = None,
    prefix: str = "tito",
    tenant_id: str | None = None,
) -> str:
    metrics = get_metrics(connection, queue_table, timeout_seconds, tenant_id)
    lines = [
        f"# HELP {prefix}_queue_length Anzahl der Jobs in der Warteschlange.",
        f"# TYPE {prefix}_queue_length gauge",
        f"{prefix}_queue_length {metrics['queue_length']}",
        f"# HELP {prefix}_active_workers Anzahl der registrierten Worker.",
        f"# TYPE {prefix}_active_workers gauge",
        f"{prefix}_active_workers {metrics['active_workers']}",
        f"# HELP {prefix}_dead_letter_queue_size Größe der Dead Letter Queue.",
        f"# TYPE {prefix}_dead_letter_queue_size gauge",
        f"{prefix}_dead_letter_queue_size {metrics['dead_letter_queue_size']}",
        f"# HELP {prefix}_error_rate Fehlerquote der verarbeiteten Jobs in Prozent.",
        f"# TYPE {prefix}_error_rate gauge",
        f"{prefix}_error_rate {metrics['error_rate']}",
        f"# HELP {prefix}_average_job_duration_seconds Durchschnittliche Jobdauer in Sekunden.",
        f"# TYPE {prefix}_average_job_duration_seconds gauge",
        f"{prefix}_average_job_duration_seconds {metrics['average_job_duration_seconds']}",
        f"# HELP {prefix}_median_job_duration_seconds Median der Jobdauer in Sekunden.",
        f"# TYPE {prefix}_median_job_duration_seconds gauge",
        f"{prefix}_median_job_duration_seconds {metrics['median_job_duration_seconds']}",
        f"# HELP {prefix}_max_job_duration_seconds Maximale Jobdauer in Sekunden.",
        f"# TYPE {prefix}_max_job_duration_seconds gauge",
        f"{prefix}_max_job_duration_seconds {metrics['max_job_duration_seconds']}",
        f"# HELP {prefix}_solver_timeout_count Anzahl der Jobs, bei denen die Solverzeit das Timeout erreicht hat.",
        f"# TYPE {prefix}_solver_timeout_count gauge",
        f"{prefix}_solver_timeout_count {metrics['solver_timeout_count']}",
        f"# HELP {prefix}_solver_timeout_rate Prozentsatz der Timeout-Jobs unter gemessenen Lösungen.",
        f"# TYPE {prefix}_solver_timeout_rate gauge",
        f"{prefix}_solver_timeout_rate {metrics['solver_timeout_rate']}",
    ]

    if metrics["job_status_counts"]:
        lines.append(f"# HELP {prefix}_jobs_total Gesamtzahl der Jobs nach Status.")
        lines.append(f"# TYPE {prefix}_jobs_total gauge")
        for status, count in metrics["job_status_counts"].items():
            lines.append(f'{prefix}_jobs_total{{status="{status}"}} {count}')

    if metrics["callback_counts"]:
        lines.append(f"# HELP {prefix}_callbacks_total Gesamtzahl der Callbacks nach Status.")
        lines.append(f"# TYPE {prefix}_callbacks_total gauge")
        for status, count in metrics["callback_counts"].items():
            lines.append(f'{prefix}_callbacks_total{{status="{status}"}} {count}')

    if metrics["workers"]:
        lines.append(f"# HELP {prefix}_worker_cpu_usage_percent CPU-Auslastung des Workers.")
        lines.append(f"# TYPE {prefix}_worker_cpu_usage_percent gauge")
        lines.append(f"# HELP {prefix}_worker_ram_usage_percent RAM-Auslastung des Workers.")
        lines.append(f"# TYPE {prefix}_worker_ram_usage_percent gauge")
        lines.append(f"# HELP {prefix}_worker_active_jobs Aktive Jobs pro Worker.")
        lines.append(f"# TYPE {prefix}_worker_active_jobs gauge")
        for worker in metrics["workers"]:
            worker_id = worker.get("worker_id", "unknown")
            cpu_usage = worker.get("cpu_usage") or 0.0
            ram_usage = worker.get("ram_usage") or 0.0
            active_jobs = worker.get("active_jobs") or 0
            lines.append(f'{prefix}_worker_cpu_usage_percent{{worker_id="{worker_id}"}} {cpu_usage}')
            lines.append(f'{prefix}_worker_ram_usage_percent{{worker_id="{worker_id}"}} {ram_usage}')
            lines.append(f'{prefix}_worker_active_jobs{{worker_id="{worker_id}"}} {active_jobs}')

    return "\n".join(lines) + "\n"
