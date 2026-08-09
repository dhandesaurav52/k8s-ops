from unittest.mock import patch


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

    response_v1 = client.get("/api/v1/health")
    assert response_v1.status_code == 200
    assert response_v1.json()["status"] == "healthy"


def test_readiness_endpoint_success(client):
    with patch("cloud.app.api.health.check_db_connection", return_value=True):
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready", "database": "connected"}

        response_v1 = client.get("/api/v1/ready")
        assert response_v1.status_code == 200
        assert response_v1.json() == {"status": "ready", "database": "connected"}


def test_readiness_endpoint_db_failure(client):
    with patch("cloud.app.api.health.check_db_connection", return_value=False):
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "not_ready", "database": "disconnected"}
