import json
from unittest.mock import MagicMock, patch
import pytest

from app.ai.gemini import GeminiProvider
from app.ai.models import AIUsage, AIIncidentAnalysis


def test_gemini_provider_disabled_when_no_api_key():
    provider = GeminiProvider(api_key="")
    assert not provider.is_available()

    response = provider.analyze({"incident": {"id": "INC-001"}})
    assert response.status == "DISABLED"
    assert "GEMINI_API_KEY is not configured" in response.error_message


def test_gemini_provider_mock_successful_analysis():
    mock_llm_json = json.dumps({
        "summary": "Prometheus container failed to pull image from registry.",
        "incident_type": "ImagePullFailure",
        "severity": "MEDIUM",
        "root_cause": {
            "statement": "The image prometheus:nonexistent-tag was not found in docker.io.",
            "confidence": 0.98
        },
        "evidence": [
            {"statement": "Container state is waiting with reason ImagePullBackOff", "source": "pod.status"},
            {"statement": "Kubernetes event Failed to pull image: manifest unknown", "source": "events"}
        ],
        "impact": {
            "level": "MEDIUM",
            "statement": "Prometheus pod is in Pending phase and metrics monitoring is unavailable."
        },
        "recommendations": [
            {"priority": "HIGH", "action": "Verify image tag in deployment spec."}
        ],
        "confirmed_facts": ["Pod is Pending", "Image pull failed with manifest unknown"],
        "likely_causes": ["Image tag typo in deployment manifest"],
        "unknowns": ["Whether tag was recently deleted from registry"],
        "next_checks": ["Check recent git commits modifying deployment image tag"]
    })

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = mock_llm_json
    mock_response.usage_metadata = MagicMock(prompt_token_count=150, candidates_token_count=200)
    mock_client.models.generate_content.return_value = mock_response

    provider = GeminiProvider(api_key="test-api-key", model_name="gemini-3.6-flash")
    with patch.object(provider, "_get_client", return_value=mock_client):
        res = provider.analyze({"incident": {"id": "INC-100"}}, incident_id="INC-100")

    assert res.status == "SUCCESS"
    assert res.provider == "gemini"
    assert res.model == "gemini-3.6-flash"
    assert res.result is not None
    assert res.result["summary"] == "Prometheus container failed to pull image from registry."
    assert res.result["root_cause"]["confidence"] == 0.98
    assert len(res.result["evidence"]) == 2
    assert len(res.result["confirmed_facts"]) == 2
    assert len(res.result["likely_causes"]) == 1
    assert len(res.result["unknowns"]) == 1

    # Usage calculation
    assert res.usage is not None
    assert res.usage["input_tokens"] == 150
    assert res.usage["output_tokens"] == 200
    assert res.usage["total_tokens"] == 350
    assert res.usage["estimated_cost_usd"] > 0.0


def test_cost_calculation():
    usage = AIUsage.calculate_cost(
        provider="gemini",
        model="gemini-3.6-flash",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        duration_ms=500.0,
        incident_id="INC-101",
        input_cost_per_m=0.10,
        output_cost_per_m=0.40,
    )
    assert usage.input_tokens == 1_000_000
    assert usage.output_tokens == 1_000_000
    assert usage.total_tokens == 2_000_000
    assert usage.estimated_cost_usd == 0.50  # 0.10 + 0.40
