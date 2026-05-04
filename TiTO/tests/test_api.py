import base64
import hashlib
import hmac
import json
import tempfile
import time
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
    settings = Settings.from_env({
        "DATABASE_URL": f"sqlite:///{db_file}",
        "API_TOKENS": "test-token"
    })
    app = create_app(settings)
    client = app.test_client()
    headers = {"Authorization": "Bearer test-token"}

    payload = {
        "metadata": {"jobId": "job-api-test", "priority": 2},
        "config": {},
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
    }

    post_response = client.post("/jobs", json=payload, headers=headers)
    assert post_response.status_code == 201
    assert post_response.json["status"] == "queued"

    list_response = client.get("/jobs", headers=headers)
    assert list_response.status_code == 200
    assert any(job["status"] == "queued" for job in list_response.json)


def test_worker_token_restricted_to_worker_endpoints(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    settings = Settings.from_env({
        "DATABASE_URL": f"sqlite:///{db_file}",
        "API_TOKEN_ROLES": "worker-token=worker"
    })
    app = create_app(settings)
    client = app.test_client()
    worker_headers = {"Authorization": "Bearer worker-token"}

    register_response = client.post("/workers/register", json={
        "worker_id": "worker-2",
        "cpu_usage": 10.0,
        "ram_usage": 20.0,
    }, headers=worker_headers)
    assert register_response.status_code == 200

    post_response = client.post("/jobs", json={
        "metadata": {"jobId": "job-worker-test", "priority": 1},
        "config": {},
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
    }, headers=worker_headers)
    assert post_response.status_code == 403
    assert post_response.json["error"] == "Forbidden"


def test_admin_token_can_access_jobs(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    settings = Settings.from_env({
        "DATABASE_URL": f"sqlite:///{db_file}",
        "API_TOKEN_ROLES": "admin-token=admin"
    })
    app = create_app(settings)
    client = app.test_client()
    headers = {"Authorization": "Bearer admin-token"}

    payload = {
        "metadata": {"jobId": "job-admin-test", "priority": 2},
        "config": {},
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
    }
    post_response = client.post("/jobs", json=payload, headers=headers)
    assert post_response.status_code == 201
    assert post_response.json["status"] == "queued"

    list_response = client.get("/jobs", headers=headers)
    assert list_response.status_code == 200
    assert any(job["status"] == "queued" for job in list_response.json)


def test_job_enqueue_requires_auth(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    settings = Settings.from_env({
        "DATABASE_URL": f"sqlite:///{db_file}",
        "API_TOKENS": "test-token"
    })
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
    assert post_response.status_code == 401
    assert post_response.json["error"] == "Unauthorized"


def test_metrics_with_auth(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    settings = Settings.from_env({
        "DATABASE_URL": f"sqlite:///{db_file}",
        "API_TOKENS": "test-token"
    })
    app = create_app(settings)
    client = app.test_client()
    headers = {"Authorization": "Bearer test-token"}

    response = client.get("/metrics", headers=headers)
    assert response.status_code == 200
    assert response.json["queue_length"] == 0
    assert response.json["active_workers"] == 0


def _create_jwt(secret: str, role: str, audience: str | None = None, issuer: str | None = None) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
    }
    if audience:
        payload["aud"] = audience
    if issuer:
        payload["iss"] = issuer

    def b64encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    header_b64 = b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = b64encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def test_worker_register_and_job_queue(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    settings = Settings.from_env({
        "DATABASE_URL": f"sqlite:///{db_file}",
        "API_TOKENS": "test-token"
    })
    app = create_app(settings)
    client = app.test_client()
    headers = {"Authorization": "Bearer test-token"}

    register_response = client.post("/workers/register", json={
        "worker_id": "worker-1",
        "cpu_usage": 1.5,
        "ram_usage": 7.2,
    }, headers=headers)
    assert register_response.status_code == 200
    assert register_response.json["status"] == "registered"

    payload = {
        "metadata": {"jobId": "job-queue-test", "priority": 3},
        "config": {},
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
    }
    post_response = client.post("/jobs", json=payload, headers=headers)
    assert post_response.status_code == 201
    assert post_response.json["status"] == "queued"

    list_response = client.get("/jobs", headers=headers)
    assert list_response.status_code == 200
    assert any(job["status"] == "queued" for job in list_response.json)


def test_jwt_admin_token_allows_jobs(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    secret = "super-secret"
    settings = Settings.from_env({
        "DATABASE_URL": f"sqlite:///{db_file}",
        "JWT_SECRET": secret,
        "JWT_ALGORITHMS": "HS256",
    })
    app = create_app(settings)
    client = app.test_client()
    token = _create_jwt(secret, "admin")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "metadata": {"jobId": "job-jwt-admin-test", "priority": 2},
        "config": {},
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
    }

    post_response = client.post("/jobs", json=payload, headers=headers)
    assert post_response.status_code == 201
    assert post_response.json["status"] == "queued"

    list_response = client.get("/jobs", headers=headers)
    assert list_response.status_code == 200
    assert any(job["status"] == "queued" for job in list_response.json)


def test_api_key_header_support(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    settings = Settings.from_env({
        "DATABASE_URL": f"sqlite:///{db_file}",
        "API_TOKENS": "header-token"
    })
    app = create_app(settings)
    client = app.test_client()
    headers = {"X-API-Key": "header-token"}

    response = client.get("/metrics", headers=headers)
    assert response.status_code == 200
    assert response.json["queue_length"] == 0
