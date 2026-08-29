import base64
import hashlib
import hmac
import json
import time
from pathlib import Path

from tito.api import create_app
from tito.config import Settings


def _valid_job_payload(**overrides) -> dict:
    """Minimal gültiges JobPayload gemäß Schema (tenantId + config Pflichtfelder)."""
    payload = {
        "metadata": {"jobId": "job-test", "tenantId": 1, "priority": 2},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-31"},
        "shiftTemplates": [],
        "requirements": [],
        "employees": [],
    }
    payload.update(overrides)
    return payload


def test_health_check():
    settings = Settings.from_env({"DATABASE_URL": "sqlite:///:memory:"})
    app = create_app(settings)
    client = app.test_client()

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_job_enqueue_and_list(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    settings = Settings.from_env({"DATABASE_URL": f"sqlite:///{db_file}", "API_TOKENS": "test-token"})
    app = create_app(settings)
    client = app.test_client()
    headers = {"Authorization": "Bearer test-token"}

    payload = _valid_job_payload(metadata={"jobId": "job-api-test", "tenantId": 1, "priority": 2})

    post_response = client.post("/jobs", json=payload, headers=headers)
    assert post_response.status_code == 201
    assert post_response.json["status"] == "queued"

    list_response = client.get("/jobs", headers=headers)
    assert list_response.status_code == 200
    assert any(job["status"] == "queued" for job in list_response.json)


def test_worker_token_restricted_to_worker_endpoints(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    settings = Settings.from_env(
        {
            "DATABASE_URL": f"sqlite:///{db_file}",
            "API_TOKEN_ROLES": "worker-token=worker",
        }
    )
    app = create_app(settings)
    client = app.test_client()
    worker_headers = {"Authorization": "Bearer worker-token"}

    register_response = client.post(
        "/workers/register",
        json={
            "worker_id": "worker-2",
            "cpu_usage": 10.0,
            "ram_usage": 20.0,
        },
        headers=worker_headers,
    )
    assert register_response.status_code == 200

    post_response = client.post(
        "/jobs",
        json={
            "metadata": {"jobId": "job-worker-test", "priority": 1},
            "config": {},
            "shiftTemplates": [],
            "requirements": [],
            "employees": [],
        },
        headers=worker_headers,
    )
    assert post_response.status_code == 403
    assert post_response.json["error"] == "Forbidden"


def test_admin_token_can_access_jobs(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    settings = Settings.from_env({"DATABASE_URL": f"sqlite:///{db_file}", "API_TOKEN_ROLES": "admin-token=admin"})
    app = create_app(settings)
    client = app.test_client()
    headers = {"Authorization": "Bearer admin-token"}

    payload = _valid_job_payload(metadata={"jobId": "job-admin-test", "tenantId": 1, "priority": 2})
    post_response = client.post("/jobs", json=payload, headers=headers)
    assert post_response.status_code == 201
    assert post_response.json["status"] == "queued"

    list_response = client.get("/jobs", headers=headers)
    assert list_response.status_code == 200
    assert any(job["status"] == "queued" for job in list_response.json)


def test_job_enqueue_requires_auth(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    settings = Settings.from_env({"DATABASE_URL": f"sqlite:///{db_file}", "API_TOKENS": "test-token"})
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
    settings = Settings.from_env({"DATABASE_URL": f"sqlite:///{db_file}", "API_TOKENS": "test-token"})
    app = create_app(settings)
    client = app.test_client()
    headers = {"Authorization": "Bearer test-token"}

    response = client.get("/metrics", headers=headers)
    assert response.status_code == 200
    assert response.json["queue_length"] == 0
    assert response.json["active_workers"] == 0
    assert response.json["job_status_counts"] == {}
    assert response.json["dead_letter_queue_size"] == 0
    assert response.json["error_rate"] == 0.0


def test_metrics_prometheus_endpoint(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    settings = Settings.from_env({"DATABASE_URL": f"sqlite:///{db_file}", "API_TOKENS": "test-token"})
    app = create_app(settings)
    client = app.test_client()
    headers = {"Authorization": "Bearer test-token"}

    response = client.get("/metrics/prometheus", headers=headers)
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/plain")
    body = response.get_data(as_text=True)
    assert "tito_queue_length" in body
    assert "tito_active_workers" in body
    assert "tito_error_rate" in body
    assert "tito_dead_letter_queue_size" in body


def test_openapi_json_endpoint(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    settings = Settings.from_env({"DATABASE_URL": f"sqlite:///{db_file}", "API_TOKENS": "test-token"})
    app = create_app(settings)
    client = app.test_client()

    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json["openapi"] == "3.0.0"
    assert response.json["info"]["title"] == "TiTO API"
    assert "/jobs" in response.json["paths"]
    assert "JobPayload" in response.json["components"]["schemas"]


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
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = b64encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def test_worker_register_and_job_queue(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    settings = Settings.from_env({"DATABASE_URL": f"sqlite:///{db_file}", "API_TOKENS": "test-token"})
    app = create_app(settings)
    client = app.test_client()
    headers = {"Authorization": "Bearer test-token"}

    register_response = client.post(
        "/workers/register",
        json={
            "worker_id": "worker-1",
            "cpu_usage": 1.5,
            "ram_usage": 7.2,
        },
        headers=headers,
    )
    assert register_response.status_code == 200
    assert register_response.json["status"] == "registered"

    payload = _valid_job_payload(metadata={"jobId": "job-queue-test", "tenantId": 1, "priority": 3})
    post_response = client.post("/jobs", json=payload, headers=headers)
    assert post_response.status_code == 201
    assert post_response.json["status"] == "queued"

    list_response = client.get("/jobs", headers=headers)
    assert list_response.status_code == 200
    assert any(job["status"] == "queued" for job in list_response.json)


def test_jwt_admin_token_allows_jobs(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    secret = "super-secret"
    settings = Settings.from_env(
        {
            "DATABASE_URL": f"sqlite:///{db_file}",
            "JWT_SECRET": secret,
            "JWT_ALGORITHMS": "HS256",
        }
    )
    app = create_app(settings)
    client = app.test_client()
    token = _create_jwt(secret, "admin")
    headers = {"Authorization": f"Bearer {token}"}

    payload = _valid_job_payload(metadata={"jobId": "job-jwt-admin-test", "tenantId": 1, "priority": 2})

    post_response = client.post("/jobs", json=payload, headers=headers)
    assert post_response.status_code == 201
    assert post_response.json["status"] == "queued"

    list_response = client.get("/jobs", headers=headers)
    assert list_response.status_code == 200
    assert any(job["status"] == "queued" for job in list_response.json)


def test_api_key_header_support(tmp_path: Path):
    db_file = tmp_path / "api_tito.db"
    settings = Settings.from_env({"DATABASE_URL": f"sqlite:///{db_file}", "API_TOKENS": "header-token"})
    app = create_app(settings)
    client = app.test_client()
    headers = {"X-API-Key": "header-token"}

    response = client.get("/metrics", headers=headers)
    assert response.status_code == 200
    assert response.json["queue_length"] == 0


# ============================================================================
# Tenant-Isolation Tests (B1-B10)
# ============================================================================


def _tenant_settings(tmp_path: Path, tenant_a: str = "1", tenant_b: str = "2") -> tuple[Settings, dict, dict]:
    """Settings mit zwei mandanten-scoped Admin-Tokens + einem Admin ohne Tenant-Mapping."""
    db_file = tmp_path / "tenant_iso.db"
    settings = Settings.from_env(
        {
            "DATABASE_URL": f"sqlite:///{db_file}",
            "API_TOKEN_ROLES": "tokenA=admin,tokenB=admin,tokenAdmin=admin",
            "API_TOKEN_TENANTS": f"tokenA={tenant_a},tokenB={tenant_b}",
        }
    )
    headers_a = {"Authorization": "Bearer tokenA"}
    headers_b = {"Authorization": "Bearer tokenB"}
    headers_admin = {"Authorization": "Bearer tokenAdmin"}
    return settings, {"a": headers_a, "b": headers_b, "admin": headers_admin}


def test_post_job_rejects_tenant_mismatch(tmp_path: Path):
    """B1: Ein mandanten-scoped Token darf nicht für einen fremden Tenant einreichen."""
    settings, headers = _tenant_settings(tmp_path)
    app = create_app(settings)
    client = app.test_client()

    payload = _valid_job_payload(metadata={"jobId": "job-cross", "tenantId": 2, "priority": 1})
    response = client.post("/jobs", json=payload, headers=headers["a"])
    assert response.status_code == 403
    assert response.json["error"] == "Forbidden"


def test_post_job_forces_authenticated_tenant(tmp_path: Path):
    """B1: Ein scoped Token mit passender tenantId darf einreichen."""
    settings, headers = _tenant_settings(tmp_path)
    app = create_app(settings)
    client = app.test_client()

    payload = _valid_job_payload(metadata={"jobId": "job-ok", "tenantId": 1, "priority": 1})
    response = client.post("/jobs", json=payload, headers=headers["a"])
    assert response.status_code == 201


def test_post_job_validates_schema_at_enqueue(tmp_path: Path):
    """B3: Payload ohne tenantId wird an der API-Grenze abgelehnt (400, nicht 201)."""
    settings, _ = _tenant_settings(tmp_path)
    app = create_app(settings)
    client = app.test_client()

    payload = _valid_job_payload()
    del payload["metadata"]["tenantId"]
    response = client.post("/jobs", json=payload, headers={"Authorization": "Bearer tokenAdmin"})
    assert response.status_code == 400


def test_jobs_list_tenant_scoped(tmp_path: Path):
    """B7: Tenant A sieht nur eigene Jobs, nicht die von Tenant B."""
    settings, headers = _tenant_settings(tmp_path)
    app = create_app(settings)
    client = app.test_client()

    client.post("/jobs", json=_valid_job_payload(metadata={"jobId": "job-a", "tenantId": 1}), headers=headers["a"])
    client.post("/jobs", json=_valid_job_payload(metadata={"jobId": "job-b", "tenantId": 2}), headers=headers["b"])

    resp_a = client.get("/jobs", headers=headers["a"])
    assert resp_a.status_code == 200
    assert len(resp_a.json) == 1

    resp_b = client.get("/jobs", headers=headers["b"])
    assert len(resp_b.json) == 1


def test_jobs_list_admin_sees_all(tmp_path: Path):
    """B7: Admin ohne Tenant-Mapping sieht alle Jobs."""
    settings, headers = _tenant_settings(tmp_path)
    app = create_app(settings)
    client = app.test_client()

    client.post("/jobs", json=_valid_job_payload(metadata={"jobId": "job-a", "tenantId": 1}), headers=headers["a"])
    client.post("/jobs", json=_valid_job_payload(metadata={"jobId": "job-b", "tenantId": 2}), headers=headers["b"])

    resp = client.get("/jobs", headers=headers["admin"])
    assert resp.status_code == 200
    assert len(resp.json) == 2


def test_get_job_status_cross_tenant_404(tmp_path: Path):
    """B8: Tenant A kann den Job von Tenant B nicht abfragen (404)."""
    settings, headers = _tenant_settings(tmp_path)
    app = create_app(settings)
    client = app.test_client()

    resp_post = client.post(
        "/jobs", json=_valid_job_payload(metadata={"jobId": "job-b", "tenantId": 2}), headers=headers["b"]
    )
    job_id = resp_post.json["jobId"]

    resp = client.get(f"/jobs/{job_id}", headers=headers["a"])
    assert resp.status_code == 404


def test_callbacks_pending_tenant_scoped(tmp_path: Path):
    """B4: /callbacks/pending liefert nur Callbacks des authentifizierten Tenants."""
    from tito.db import enqueue_callback, enqueue_job, get_connection

    settings, headers = _tenant_settings(tmp_path)
    app = create_app(settings)
    client = app.test_client()

    conn = get_connection(settings.database_url)
    payload_a = _valid_job_payload(metadata={"jobId": "cb-a", "tenantId": 1})
    payload_b = _valid_job_payload(metadata={"jobId": "cb-b", "tenantId": 2})
    job_a = enqueue_job(conn, payload_a, settings.queue_table, tenant_id="1")
    job_b = enqueue_job(conn, payload_b, settings.queue_table, tenant_id="2")
    enqueue_callback(conn, job_a, "http://a/callback", {"status": "ok"}, tenant_id="1")
    enqueue_callback(conn, job_b, "http://b/callback", {"status": "ok"}, tenant_id="2")

    resp_a = client.get("/callbacks/pending", headers=headers["a"])
    assert resp_a.status_code == 200
    assert resp_a.json["count"] == 1
    assert resp_a.json["callbacks"][0]["callback_url"] == "http://a/callback"

    resp_admin = client.get("/callbacks/pending", headers=headers["admin"])
    assert resp_admin.json["count"] == 2


def test_metrics_tenant_scoped(tmp_path: Path):
    """B5: /metrics zählt nur Jobs des authentifizierten Tenants."""
    settings, headers = _tenant_settings(tmp_path)
    app = create_app(settings)
    client = app.test_client()

    for i in range(3):
        client.post(
            "/jobs", json=_valid_job_payload(metadata={"jobId": f"job-a-{i}", "tenantId": 1}), headers=headers["a"]
        )
    client.post("/jobs", json=_valid_job_payload(metadata={"jobId": "job-b", "tenantId": 2}), headers=headers["b"])

    resp_a = client.get("/metrics", headers=headers["a"])
    assert resp_a.status_code == 200
    assert resp_a.json["queue_length"] == 3

    resp_b = client.get("/metrics", headers=headers["b"])
    assert resp_b.json["queue_length"] == 1

    resp_admin = client.get("/metrics", headers=headers["admin"])
    assert resp_admin.json["queue_length"] == 4


def test_metrics_prometheus_tenant_scoped(tmp_path: Path):
    """B5: Prometheus-Export ist mandanten-scoped."""
    settings, headers = _tenant_settings(tmp_path)
    app = create_app(settings)
    client = app.test_client()

    client.post("/jobs", json=_valid_job_payload(metadata={"jobId": "job-a", "tenantId": 1}), headers=headers["a"])
    client.post("/jobs", json=_valid_job_payload(metadata={"jobId": "job-b", "tenantId": 2}), headers=headers["b"])

    resp_a = client.get("/metrics/prometheus", headers=headers["a"])
    assert resp_a.status_code == 200
    body = resp_a.get_data(as_text=True)
    assert "tito_queue_length 1" in body


def test_dlq_cross_tenant_empty(tmp_path: Path):
    """B4: DLQ eines Tenants enthält nicht die Jobs eines anderen."""
    from tito.db import enqueue_job, get_connection, move_job_to_dlq

    settings, headers = _tenant_settings(tmp_path)
    app = create_app(settings)
    client = app.test_client()

    conn = get_connection(settings.database_url)
    payload_a = _valid_job_payload(metadata={"jobId": "dlq-a", "tenantId": 1})
    payload_b = _valid_job_payload(metadata={"jobId": "dlq-b", "tenantId": 2})
    job_a = enqueue_job(conn, payload_a, settings.queue_table, tenant_id="1")
    job_b = enqueue_job(conn, payload_b, settings.queue_table, tenant_id="2")

    move_job_to_dlq(conn, job_a, payload_a, "fail", 1, tenant_id="1")
    move_job_to_dlq(conn, job_b, payload_b, "fail", 1, tenant_id="2")

    resp_a = client.get("/dlq", headers=headers["a"])
    assert resp_a.status_code == 200
    assert resp_a.json["count"] == 1

    resp_admin = client.get("/dlq", headers=headers["admin"])
    assert resp_admin.json["count"] == 2


def test_worker_token_cannot_access_jobs(tmp_path: Path):
    """B9: Ein Worker-Token (Rolle 'worker') kann keine Jobs einreichen oder abfragen."""
    db_file = tmp_path / "worker_role.db"
    settings = Settings.from_env(
        {"DATABASE_URL": f"sqlite:///{db_file}", "API_TOKEN_ROLES": "wtoken=worker,jtoken=jobs"}
    )
    app = create_app(settings)
    client = app.test_client()
    w_headers = {"Authorization": "Bearer wtoken"}

    # Worker kann sich registrieren
    reg = client.post(
        "/workers/register", json={"worker_id": "w1", "cpu_usage": 1.0, "ram_usage": 2.0}, headers=w_headers
    )
    assert reg.status_code == 200

    # Worker kann keine Jobs einreichen
    payload = _valid_job_payload(metadata={"jobId": "job-w", "tenantId": 1})
    post_resp = client.post("/jobs", json=payload, headers=w_headers)
    assert post_resp.status_code == 403

    # Worker kann keine Jobs abfragen
    list_resp = client.get("/jobs", headers=w_headers)
    assert list_resp.status_code == 403
