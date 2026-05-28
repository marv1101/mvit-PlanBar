def test_ping_endpoint(client):
    response = client.get("/api/v1/health/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_endpoint(client):
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_db_health(client):
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_tito_health(client):
    response = client.get("/api/v1/health/tito")
    assert response.status_code == 200
    assert "status" in response.json()
