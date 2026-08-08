from unittest.mock import MagicMock, patch
import pytest

from app.ai.gemini import GeminiProvider


def test_ai_resilience_transient_error_retries_and_fails_gracefully():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("503 Service Unavailable / Server Overloaded")

    provider = GeminiProvider(api_key="test-key", max_retries=2)
    with patch.object(provider, "_get_client", return_value=mock_client), patch("time.sleep"):
        res = provider.analyze({"incident": {"id": "INC-ERR-1"}}, incident_id="INC-ERR-1")

    assert res.status == "FAILED"
    assert "Gemini API request failed after 3 attempts" in res.error_message
    assert mock_client.models.generate_content.call_count == 3  # Initial + 2 retries


def test_ai_resilience_non_retryable_auth_error_fails_fast():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API_KEY_INVALID: 401 Unauthorized")

    provider = GeminiProvider(api_key="invalid-key", max_retries=2)
    with patch.object(provider, "_get_client", return_value=mock_client), patch("time.sleep") as mock_sleep:
        res = provider.analyze({"incident": {"id": "INC-AUTH-1"}}, incident_id="INC-AUTH-1")

    assert res.status == "FAILED"
    # Should stop retrying immediately on 401/invalid key
    assert mock_client.models.generate_content.call_count == 1
    mock_sleep.assert_not_called()


def test_ai_resilience_malformed_json_response():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is not valid JSON content { broken..."
    mock_response.usage_metadata = MagicMock(prompt_token_count=50, candidates_token_count=10)
    mock_client.models.generate_content.return_value = mock_response

    provider = GeminiProvider(api_key="test-key")
    with patch.object(provider, "_get_client", return_value=mock_client):
        res = provider.analyze({"incident": {"id": "INC-JSON-1"}}, incident_id="INC-JSON-1")

    assert res.status == "FAILED_TO_PARSE"
    assert "invalid or non-schema JSON" in res.error_message
