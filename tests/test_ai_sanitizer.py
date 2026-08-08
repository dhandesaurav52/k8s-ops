import json
import pytest
from app.ai.sanitizer import EvidenceSanitizer


def test_sanitizer_removes_secrets_and_credentials():
    raw_evidence = {
        "incident_id": "INC-TEST-001",
        "category": "CrashLoop",
        "current_state": "CrashLoopBackOff",
        "status": "OPEN",
        "resource": {"kind": "Pod", "name": "app-pod", "namespace": "prod", "uid": "uid-app"},
        "diagnosis": {"severity": "HIGH", "category": "CrashLoop"},
        "investigation": {
            "findings": [{"category": "POD", "message": "Container crashed"}],
            "pod": {
                "name": "app-pod",
                "containers": [
                    {
                        "name": "web",
                        "image": "my-app:v1",
                        "env": [
                            {"name": "PORT", "value": "8080"},
                            {"name": "DB_PASSWORD", "value": "SUPER_SECRET_PASSWORD_123"},
                            {"name": "API_SECRET_KEY", "value": "VERY_SECRET_TOKEN_456"},
                        ],
                    }
                ],
            },
            "secrets": [
                {
                    "name": "db-secret",
                    "namespace": "prod",
                    "data": {"password": "SUPER_SECRET_PASSWORD_123", "token": "VERY_SECRET_TOKEN_456"},
                    "stringData": {"api_key": "RAW_API_KEY_789"},
                }
            ],
            "events": [
                {
                    "type": "Warning",
                    "reason": "BackOff",
                    "message": "Back-off restarting failed container web " + ("x" * 500),
                }
            ],
        },
    }

    sanitized = EvidenceSanitizer.sanitize(raw_evidence)
    sanitized_json = json.dumps(sanitized)

    # 1. Assert sensitive strings are completely absent from payload
    assert "SUPER_SECRET_PASSWORD_123" not in sanitized_json
    assert "VERY_SECRET_TOKEN_456" not in sanitized_json
    assert "RAW_API_KEY_789" not in sanitized_json

    # 2. Assert Secret data/stringData dicts are stripped
    secrets = sanitized.get("secrets", [])
    assert len(secrets) == 1
    assert secrets[0]["name"] == "db-secret"
    assert "data" not in secrets[0]
    assert "stringData" not in secrets[0]

    # 3. Assert sensitive env vars are masked
    pod = sanitized.get("pod", {})
    env = pod["containers"][0]["env"]
    env_dict = {item["name"]: item["value"] for item in env}
    assert env_dict["PORT"] == "8080"
    assert env_dict["DB_PASSWORD"] == "[REDACTED]"
    assert env_dict["API_SECRET_KEY"] == "[REDACTED]"

    # 4. Assert long event message was truncated
    events = sanitized.get("events", [])
    assert len(events) == 1
    assert "TRUNCATED" in events[0]["message"]
    assert len(events[0]["message"]) <= EvidenceSanitizer.MAX_EVENT_MESSAGE_LENGTH + 20
