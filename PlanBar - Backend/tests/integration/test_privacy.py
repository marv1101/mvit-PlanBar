def test_privacy_endpoint_returns_200(client):
    response = client.get("/api/v1/privacy")
    assert response.status_code == 200


def test_privacy_endpoint_public(client):
    """No auth required - endpoint is publicly accessible."""
    response = client.get("/api/v1/privacy")
    assert response.status_code == 200


def test_privacy_contains_required_fields(client):
    response = client.get("/api/v1/privacy")
    data = response.json()

    assert data["title"] == "Datenschutzerklärung"
    assert "controller" in data
    assert "data_categories" in data
    assert "data_subject_rights" in data
    assert "complaint_right" in data
    assert "third_country_transfer" in data
    assert "contact" in data


def test_privacy_controller_has_required_info(client):
    response = client.get("/api/v1/privacy")
    controller = response.json()["controller"]

    assert "name" in controller
    assert "address" in controller
    assert "email" in controller


def test_privacy_data_subject_rights_are_complete(client):
    response = client.get("/api/v1/privacy")
    rights = response.json()["data_subject_rights"]

    assert "access" in rights
    assert "rectification" in rights
    assert "erasure" in rights
    assert "restriction" in rights
    assert "data_portability" in rights
    assert "objection" in rights


def test_privacy_has_data_categories(client):
    response = client.get("/api/v1/privacy")
    categories = response.json()["data_categories"]

    assert len(categories) >= 1
    for cat in categories:
        assert "category" in cat
        assert "data" in cat
        assert "purpose" in cat
        assert "legal_basis" in cat
        assert "retention" in cat


def test_privacy_has_contact(client):
    response = client.get("/api/v1/privacy")
    contact = response.json()["contact"]

    assert "role" in contact
    assert "email" in contact
