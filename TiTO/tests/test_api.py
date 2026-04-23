import tempfile
from pathlib import Path

from tito.api import create_app
from tito.config import Settings


def test_health_check():
    settings = Settings.from_env({"DATABASE_URL": "sqlite:///:memory:"})
    app = create_app(settings)
    client = app.test_client()

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_job_enqueue_and_list(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    settings = Settings.from_env({"DATABASE_URL": f"sqlite:///{db_file}"})
    app = create_app(settings)
    client = app.test_client()

    payload = {
        "metadata": {"jobId": "job-api-test", "priority": 2},
        "config": {},
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
    }

    post_response = client.post("/jobs", json=payload)
    assert post_response.status_code == 201
    assert post_response.json["status"] == "queued"

    list_response = client.get("/jobs")
    assert list_response.status_code == 200
    assert any(job["job_id"] == "job-api-test" for job in list_response.json)
