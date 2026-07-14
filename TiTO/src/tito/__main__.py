import argparse
from .config import Settings
from .api import create_app
from .db import get_connection, enqueue_job
from .worker import run_worker


def _seed_example_job(connection, queue_table: str) -> str:
    example_payload = {
        "metadata": {
            "jobId": "job-0001",
            "tenantId": 42,
            "priority": 1,
            "timestamp": "2026-04-22T10:00:00Z",
        },
        "config": {
            "schemaVersion": "1.0",
            "startDate": "2026-01-01",
            "endDate": "2026-01-31",
            "maxConsecutiveDays": 6,
            "minRestTimeHours": 11,
        },
        "shiftTemplates": [
            {
                "id": "S_FRUEH",
                "name": "Frühschicht",
                "startTime": "06:00",
                "endTime": "14:00",
                "minBreakMinutes": 30,
            }
        ],
        "requirements": [
            {
                "date": "2026-01-02",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {
                "date": "2026-01-03",
                "shiftId": "S_FRUEH",
                "neededSkills": {"Apotheker": 1},
            },
            {
                "date": "2026-01-02",
                "shiftId": "S_SPAET",
                "neededSkills": {"Apotheker": 1},
            },
        ],
        "employees": [
            {
                "id": "emp_001",
                "name": "Max Mustermann",
                "contract": {
                    "weeklyHours": 40.0,
                    "employmentType": "Apotheker",
                    "currentBalanceHours": 5.5,
                },
                "skills": ["Apotheker"],
                "forbiddenDates": [],
                "breakMinutes": 30,  # Individuelle Pause in Minuten
            },
            {
                "id": "emp_002",
                "name": "Max Musterhausen",
                "contract": {
                    "weeklyHours": 35.0,
                    "employmentType": "Apotheker",
                    "currentBalanceHours": 3,
                },
                "skills": ["Apotheker"],
                "forbiddenDates": ["2026-01-02"],
                "breakMinutes": 45,  # Längere Pause für diesen Employee
            },
        ],
        "wishes": [
            {
                "employeeId": "emp_001",
                "type": "PREFER_SHIFT",
                "shiftId": "S_FRUEH",
                "date": "2026-01-02",
                "weight": 2,
                "comment": "Frühschicht bevorzugt",
            }
        ],
    }
    enqueue_job(connection, example_payload, queue_table)
    return example_payload["metadata"]["jobId"]


def get_app():
    """Initialisiert die Flask-App für Gunicorn."""
    from .config import Settings

    settings = Settings.from_env()
    return create_app(settings)


def main() -> None:
    parser = argparse.ArgumentParser(description="TiTO minimal runnable worker and API")
    parser.add_argument("--mode", choices=["api", "worker", "seed"], default="api")
    parser.add_argument("--port", type=int, default=5001)
    args = parser.parse_args()

    settings = Settings.from_env()

    if args.mode == "api":
        app = create_app(settings)
        app.run(host="0.0.0.0", port=args.port)
    elif args.mode == "worker":
        run_worker(settings)
    elif args.mode == "seed":
        connection = get_connection(settings.database_url)
        job_id = _seed_example_job(connection, settings.queue_table)
        print(f"Seeded example job: {job_id}")
