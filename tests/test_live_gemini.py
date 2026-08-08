import os
import pytest
from app.config import GEMINI_API_KEY, SKYOPS_RUN_LIVE_AI_TEST
from app.ai.gemini import GeminiProvider


def test_live_gemini_integration():
    """
    Live Integration Test against Google Gemini API.
    Runs ONLY when SKYOPS_RUN_LIVE_AI_TEST=true AND GEMINI_API_KEY is configured.
    Otherwise skips cleanly without making network calls or spending credits.
    """
    if not SKYOPS_RUN_LIVE_AI_TEST or not GEMINI_API_KEY:
        pytest.skip(
            "Live Gemini test skipped. Enable by setting SKYOPS_RUN_LIVE_AI_TEST=true "
            "and configuring GEMINI_API_KEY."
        )

    provider = GeminiProvider(api_key=GEMINI_API_KEY)
    sample_evidence = {
        "incident": {
            "id": "INC-LIVE-TEST",
            "category": "ImagePullFailure",
            "state": "ImagePullBackOff",
            "severity": "MEDIUM",
        },
        "target": {"kind": "Pod", "namespace": "default", "name": "live-test-pod"},
        "pod": {
            "phase": "Pending",
            "containers": [
                {
                    "name": "app",
                    "image": "nginx:nonexistent-tag-skyops-test-999",
                    "ready": False,
                    "restart_count": 0,
                    "state": "waiting",
                    "reason": "ImagePullBackOff",
                }
            ],
        },
        "events": [
            {
                "type": "Warning",
                "reason": "Failed",
                "message": "Failed to pull image nginx:nonexistent-tag-skyops-test-999: manifest unknown",
            }
        ],
    }

    res = provider.analyze(sample_evidence, incident_id="INC-LIVE-TEST")

    assert res.status == "SUCCESS"
    assert res.result is not None
    assert "summary" in res.result
    assert "root_cause" in res.result
    assert res.result["root_cause"]["confidence"] > 0.0
    assert res.usage is not None
    assert res.usage["total_tokens"] > 0
