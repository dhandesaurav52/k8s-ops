import pytest
from fastapi.testclient import TestClient
from cloud.app.auth import get_current_identity
from cloud.app.config import settings
from cloud.app.main import app


def test_first_run_auth_flow(client: TestClient):
    # Remove global get_current_identity override to test real auth
    app.dependency_overrides.pop(get_current_identity, None)

    # 1. Verify fresh install setup status
    res = client.get("/api/v1/auth/status")
    assert res.status_code == 200
    data = res.json()
    assert data["is_setup_completed"] is False
    assert data["authenticated"] is False
    assert data["user"] is None

    # 2. Verify invalid initial password fails
    res = client.post(
        "/api/v1/auth/verify-initial-password",
        json={"initial_password": "wrong-initial-password"},
    )
    assert res.status_code == 401
    assert "Invalid initial administrator password" in res.json()["detail"]

    # 3. Verify valid initial password passes
    res = client.post(
        "/api/v1/auth/verify-initial-password",
        json={"initial_password": settings.SKYOPS_INITIAL_ADMIN_PASSWORD},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # 4. Create administrator account
    res = client.post(
        "/api/v1/auth/setup-admin",
        json={
            "initial_password": settings.SKYOPS_INITIAL_ADMIN_PASSWORD,
            "username": "sysadmin",
            "email": "sysadmin@skyops.internal",
            "password": "SecurePassword123!",
        },
    )
    assert res.status_code == 201
    assert res.json()["status"] == "ok"

    # 5. Verify setup status is now completed
    res = client.get("/api/v1/auth/status")
    assert res.status_code == 200
    assert res.json()["is_setup_completed"] is True

    # 6. Verify initial password NO LONGER works after setup!
    res = client.post(
        "/api/v1/auth/verify-initial-password",
        json={"initial_password": settings.SKYOPS_INITIAL_ADMIN_PASSWORD},
    )
    assert res.status_code == 400
    assert "Initial setup has already been completed" in res.json()["detail"]

    # 7. Try login with wrong password
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "sysadmin", "password": "WrongPassword"},
    )
    assert res.status_code == 401

    # 8. Login with new credentials
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "sysadmin", "password": "SecurePassword123!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["user"]["username"] == "sysadmin"
    assert "token" in data
    session_token = data["token"]

    # 9. Test authenticated identity check (/api/v1/auth/me) with session token
    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert res.status_code == 200
    assert res.json()["identity"]["sub"] == "sysadmin"

    # 10. Test protected endpoints with user session token
    res = client.get(
        "/api/v1/clusters",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert res.status_code == 200

    # 11. Test protected endpoints without auth token (should return 401)
    res = client.get("/api/v1/clusters")
    assert res.status_code == 401

    # 12. Test agent authentication token continues working independently
    res = client.get(
        "/api/v1/clusters",
        headers={"Authorization": f"Bearer {settings.SKYOPS_AGENT_TOKEN}"},
    )
    assert res.status_code == 200

    # 13. Test logout clears session
    res = client.post("/api/v1/auth/logout")
    assert res.status_code == 200
    assert res.json()["status"] == "logged_out"
