import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import (
    AI_INPUT_COST_PER_MILLION_TOKENS,
    AI_MAX_RETRIES,
    AI_OUTPUT_COST_PER_MILLION_TOKENS,
    GEMINI_API_KEY,
    GEMINI_MODEL,
)
from app.ai.models import (
    AIAnalysisResponse,
    AIIncidentAnalysis,
    AIUsage,
    utc_now_iso,
)
from app.ai.provider import AIProvider

logger = logging.getLogger("SkyOps.GeminiProvider")

PROMPT_FILE = Path(__file__).parent / "prompts" / "incident_analysis.txt"


def load_system_prompt() -> str:
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8")
    return "You are SkyOps Kubernetes Incident Reasoner. Analyze the evidence and return JSON."


class GeminiProvider(AIProvider):
    """
    Google Gemini API Provider for SkyOps AI Incident Reasoning Engine.
    Uses the official google-genai SDK.
    Includes rate-limiting resilience, retry policy, token usage tracking,
    and safe JSON output parsing.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        max_retries: int = AI_MAX_RETRIES,
    ):
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = GEMINI_API_KEY
        self.model_name = model_name or GEMINI_MODEL
        self.max_retries = max_retries
        self._client = None

    @property
    def name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _get_client(self):
        if not self._client and self.is_available():
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self._client = None
        return self._client

    def analyze(self, evidence: Dict[str, Any], incident_id: str = "") -> AIAnalysisResponse:
        """
        Sends sanitized evidence payload to Gemini model and returns AIAnalysisResponse.
        If API key is missing or call fails, gracefully handles failure without breaking SkyOps.
        """
        now_iso = utc_now_iso()

        if not self.is_available():
            logger.info("AI analysis disabled: GEMINI_API_KEY is not configured.")
            return AIAnalysisResponse(
                provider=self.name,
                model=self.model_name,
                generated_at=now_iso,
                analysis_version=1,
                status="DISABLED",
                error_message="GEMINI_API_KEY is not configured.",
            )

        client = self._get_client()
        if not client:
            return AIAnalysisResponse(
                provider=self.name,
                model=self.model_name,
                generated_at=now_iso,
                analysis_version=1,
                status="UNAVAILABLE",
                error_message="Failed to initialize Gemini SDK client.",
            )

        system_prompt = load_system_prompt()
        user_content = f"INCIDENT EVIDENCE PAYLOAD:\n{json.dumps(evidence, indent=2)}"

        attempts = 0
        last_exception = None
        start_time = time.time()

        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0.1,  # Low temperature for deterministic evidence-based reasoning
        )

        while attempts <= self.max_retries:
            attempts += 1
            try:
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=user_content,
                    config=config,
                )
                duration_ms = (time.time() - start_time) * 1000.0

                raw_text = response.text or ""

                # Extract usage metadata
                input_tokens = 0
                output_tokens = 0
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                    output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
                else:
                    # Fallback token estimation
                    input_tokens = len(user_content) // 4
                    output_tokens = len(raw_text) // 4

                usage = AIUsage.calculate_cost(
                    provider=self.name,
                    model=self.model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    duration_ms=duration_ms,
                    incident_id=incident_id,
                    input_cost_per_m=AI_INPUT_COST_PER_MILLION_TOKENS,
                    output_cost_per_m=AI_OUTPUT_COST_PER_MILLION_TOKENS,
                ).to_dict()

                # Parse JSON
                parsed_analysis = self._parse_json_response(raw_text)
                if not parsed_analysis:
                    logger.warning(f"Failed to parse Gemini JSON response for incident {incident_id}")
                    return AIAnalysisResponse(
                        provider=self.name,
                        model=self.model_name,
                        generated_at=now_iso,
                        analysis_version=1,
                        status="FAILED_TO_PARSE",
                        result=None,
                        usage=usage,
                        error_message="Received invalid or non-schema JSON response from Gemini model.",
                    )

                return AIAnalysisResponse(
                    provider=self.name,
                    model=self.model_name,
                    generated_at=now_iso,
                    analysis_version=1,
                    status="SUCCESS",
                    result=parsed_analysis.to_dict(),
                    usage=usage,
                )

            except Exception as e:
                last_exception = e
                err_str = str(e).lower()
                logger.warning(f"Gemini API attempt {attempts} failed for incident {incident_id}: {e}")

                # Check if non-retryable (e.g. invalid API key, 401, 403, bad request)
                if "invalid api key" in err_str or "401" in err_str or "403" in err_str or "permission_denied" in err_str:
                    logger.error("Non-retryable authentication error encountered with Gemini API.")
                    break

                if attempts <= self.max_retries:
                    time.sleep(1.0 * attempts)  # Backoff before retry

        # All attempts failed
        duration_ms = (time.time() - start_time) * 1000.0
        return AIAnalysisResponse(
            provider=self.name,
            model=self.model_name,
            generated_at=now_iso,
            analysis_version=1,
            status="FAILED",
            error_message=f"Gemini API request failed after {attempts} attempts: {last_exception}",
            usage={
                "provider": self.name,
                "model": self.model_name,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "request_duration_ms": round(duration_ms, 2),
                "estimated_cost_usd": 0.0,
                "incident_id": incident_id,
            },
        )

    def _parse_json_response(self, raw_text: str) -> Optional[AIIncidentAnalysis]:
        """
        Safely strips markdown code blocks and parses raw text into AIIncidentAnalysis object.
        """
        if not raw_text or not raw_text.strip():
            return None

        clean_text = raw_text.strip()
        # Remove ```json ... ``` blocks if present
        if clean_text.startswith("```"):
            lines = clean_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_text = "\n".join(lines).strip()

        try:
            data = json.loads(clean_text)
            if isinstance(data, dict):
                return AIIncidentAnalysis.from_dict(data)
        except Exception as e:
            logger.error(f"JSON decoding error: {e} | Text: {clean_text[:200]}")
            return None
        return None
