import time
import uuid
import psutil
import requests
from .config import Settings
from .db import get_connection, fetch_next_job, mark_job_processing, store_result
from .schema import validate_job_payload
from .solver import build_model, solve_model


def run_worker(settings: Settings) -> None:
    """Hauptschleife des TiTO-Workers."""
    print("Starting TiTO Worker...")
    worker_id = str(uuid.uuid4())
    print(f"Worker ID: {worker_id}")
    
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
        print(f"Failed to register worker: {e}")
    
    connection = get_connection(settings.database_url)
    active_jobs = 0
    heartbeat_counter = 0
    
    while True:
        job = fetch_next_job(connection, settings.queue_table)
        if job is None:
            time.sleep(1)
            continue
        
        active_jobs += 1
        try:
            # Verwende die echte INTEGER job_id aus der DB
            db_job_id = job.pop("_db_job_id")
            mark_job_processing(connection, db_job_id)

            print(f"Processing job ID: {db_job_id}")

            validate_job_payload(job)
            model = build_model(job)
            result = solve_model(model, settings.timeout_seconds)

            store_result(connection, db_job_id, result)
        except Exception as exc:
            print(f"Job failed: {exc}")
        active_jobs -= 1
        
        # Sende Heartbeat alle 10 Jobs
        heartbeat_counter += 1
        if heartbeat_counter >= 10:
            heartbeat_counter = 0
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
                print(f"Failed to send heartbeat: {e}")
        
        time.sleep(0.1)
