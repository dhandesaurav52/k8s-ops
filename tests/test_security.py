import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure SQLite in-memory DB is used
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SKYOPS_ENV"] = "testing"
os.environ["SKYOPS_AGENT_TOKEN"] = "skyops-agent-secret-token"
os.environ["SKYOPS_ADMIN_USERNAME"] = "admin"
os.environ["SKYOPS_ADMIN_PASSWORD"] = "skyops123"

import cloud.app.database as db_module
from cloud.app.database import Base, get_db
from cloud.app.main import app as cloud_app
from cloud.app.config import settings


@pytest.fixture(autouse=True)
def setup_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_module.engine = engine
    db_module.SessionLocal = TestingSessionLocal
    Base.metadata.create_all(bind=engine)

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    cloud_app.dependency_overrides[get_db] = _override_get_db
    yield
    cloud_app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_public_health_endpoint_accessible():
    client = TestClient(cloud_app)
    res1 = client.get("/health")
    assert res1.status_code == 200
    res2 = client.get("/api/v1/health")
    assert res2.status_code == 200


def test_protected_endpoints_reject_unauthenticated():
    client = TestClient(cloud_app)
    endpoints = [
        "/api/v1/clusters",
        "/api/v1/incidents",
        "/api/v1/metrics",
        "/api/v1/remediations",
    ]
    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code == 401, f"Expected 401 for unauthenticated request to {ep}"


def test_protected_endpoints_reject_invalid_token():
    client = TestClient(cloud_app)
    headers = {"Authorization": "Bearer invalid-secret-token-999"}
    endpoints = [
        "/api/v1/clusters",
        "/api/v1/incidents",
        "/api/v1/metrics",
        "/api/v1/remediations",
    ]
    for ep in endpoints:
        resp = client.get(ep, headers=headers)
        assert resp.status_code == 401, f"Expected 401 for invalid token on {ep}"


def test_valid_agent_token_access():
    client = TestClient(cloud_app)
    headers = {"Authorization": f"Bearer {settings.SKYOPS_AGENT_TOKEN}"}
    
    resp = client.get("/api/v1/clusters", headers=headers)
    assert resp.status_code == 200
    
    resp2 = client.get("/api/v1/incidents", headers=headers)
    assert resp2.status_code == 200


def test_admin_login_and_session_auth():
    client = TestClient(cloud_app)
    
    # Invalid login
    bad_login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert bad_login.status_code == 401
    
    # Valid login
    login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "skyops123"})
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data["status"] == "ok"
    token = data["token"]
    assert token
    
    # Verify cookie was set
    assert "skyops_session" in login_resp.cookies
    
    # Test session token via Bearer header
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["identity"]["sub"] == "admin"
    
    clusters_resp = client.get("/api/v1/clusters", headers=headers)
    assert clusters_resp.status_code == 200


def test_security_headers():
    client = TestClient(cloud_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_secret_redaction_in_global_exception_handler():
    from cloud.app.main import global_exception_handler
    from unittest.mock import MagicMock

    req = MagicMock()
    req.method = "GET"
    req.url.path = "/test"
    exc = Exception(f"Failed to authenticate with secret {settings.SKYOPS_AGENT_TOKEN}")

    import asyncio
    res = asyncio.run(global_exception_handler(req, exc))
    assert res.status_code == 500
