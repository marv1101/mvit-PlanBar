"""Integration tests for double-submit cookie CSRF protection."""

from app.middleware.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME


def test_csrf_token_set_on_get(raw_client):
    """GET request returns a csrf_token cookie."""
    response = raw_client.get("/api/v1/health/ping")
    assert response.status_code == 200
    assert CSRF_COOKIE_NAME in response.cookies


def test_csrf_valid_token_accepted(raw_client):
    """POST with a matching X-CSRF-Token header succeeds."""
    # First GET to obtain the token
    get_resp = raw_client.get("/api/v1/health/ping")
    token = get_resp.cookies[CSRF_COOKIE_NAME]

    # POST with the correct header
    response = raw_client.post(
        "/api/v1/users/login",
        json={"email": "x@x.com", "password": "y"},
        headers={CSRF_HEADER_NAME: token},
    )
    # Should not be a 403 (will be 401 because credentials are wrong)
    assert response.status_code != 403


def test_csrf_missing_header_rejected(raw_client):
    """POST without X-CSRF-Token header returns 403."""
    response = raw_client.post(
        "/api/v1/users",
        json={"username": "u", "email": "u@u.com", "password": "p"},
    )
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


def test_csrf_wrong_token_rejected(raw_client):
    """POST with a wrong X-CSRF-Token header returns 403."""
    raw_client.get("/api/v1/health/ping")  # ensure cookie is set
    response = raw_client.post(
        "/api/v1/users",
        json={"username": "u", "email": "u@u.com", "password": "p"},
        headers={CSRF_HEADER_NAME: "wrong-token-value"},
    )
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


def test_csrf_get_not_checked(raw_client):
    """GET without X-CSRF-Token header succeeds."""
    response = raw_client.get("/api/v1/health/ping")
    assert response.status_code == 200
    # No CSRF header was sent; still works because GET is safe.
    assert CSRF_COOKIE_NAME in response.cookies
