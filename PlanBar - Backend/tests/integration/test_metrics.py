def test_get_metrics(client, auth_headers):
    response = client.get("/api/v1/metrics/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_schedules" in data
    assert "average_solve_time" in data


def test_get_robustness_metrics(client, auth_headers):
    response = client.get("/api/v1/metrics/robustness", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_optimal" in data
    assert "optimal_rate" in data
