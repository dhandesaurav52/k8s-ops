import logging
from typing import Any, Dict, Optional

from app.incidents.models import Incident, utc_now_iso
from app.ai.gemini import GeminiProvider
from app.ai.models import AIAnalysisResponse
from app.ai.provider import AIProvider
from app.ai.sanitizer import EvidenceSanitizer

logger = logging.getLogger("SkyOps.AIAnalyzer")


class AIAnalyzer:
    """
    AI Incident Analysis Service.
    Coordinates evidence sanitization, provider invocation, trigger intelligence,
    incident model updates, and CLI output formatting.
    """

    def __init__(self, provider: Optional[AIProvider] = None):
        self.provider = provider or GeminiProvider()

    def should_analyze(self, incident: Incident) -> bool:
        """
        Intelligent triggering:
        Returns True if AI analysis should be executed for this incident:
        1. Never analyzed before (ai_analysis is None or ai_status in ['NOT_ANALYZED', 'FAILED'])
        2. Significant state progression (state_history length changed since last analysis)
        """
        if not incident.ai_analysis or incident.ai_status in ("NOT_ANALYZED", "FAILED", "FAILED_TO_PARSE"):
            return True

        # Check if state history has grown since last analysis
        last_history_len = incident.ai_analysis.get("state_history_len_at_analysis", 0)
        if len(incident.state_history) > last_history_len:
            return True

        return False

    def analyze_incident(self, incident: Incident, force: bool = False) -> Incident:
        """
        Analyzes the given incident using the AI provider if triggered or forced.
        Updates the incident object in-place and returns it.
        """
        if not force and not self.should_analyze(incident):
            logger.debug(f"Skipping AI analysis for incident {incident.incident_id} (no material change)")
            return incident

        # 1. Prepare sanitized evidence payload
        raw_dict = incident.to_dict()
        safe_payload = EvidenceSanitizer.sanitize(raw_dict)

        # 2. Invoke AI Provider
        try:
            ai_response: AIAnalysisResponse = self.provider.analyze(
                evidence=safe_payload,
                incident_id=incident.incident_id,
            )
        except Exception as e:
            logger.error(f"Unexpected error during AI analysis execution: {e}")
            ai_response = AIAnalysisResponse(
                provider=self.provider.name,
                model=getattr(self.provider, "model_name", "unknown"),
                generated_at=utc_now_iso(),
                analysis_version=1,
                status="FAILED",
                error_message=str(e),
            )

        # 3. Update Incident fields
        res_dict = ai_response.to_dict()
        # Track history length at analysis time for trigger intelligence
        if res_dict.get("result"):
            res_dict["result"]["state_history_len_at_analysis"] = len(incident.state_history)

        incident.ai_analysis = res_dict
        incident.ai_status = ai_response.status
        incident.ai_updated_at = utc_now_iso()

        return incident

    @staticmethod
    def print_ai_analysis_cli(incident: Incident) -> None:
        """
        Prints the beautifully formatted AI Analysis section to stdout.
        """
        ai_data = incident.ai_analysis or {}
        status = incident.ai_status
        result = ai_data.get("result") or {}

        print("\n" + "=" * 60)
        print("                  SKYOPS AI ANALYSIS")
        print("=" * 60)
        print(f"\nIncident:\n{incident.incident_id}")

        if status == "SUCCESS" and result:
            summary = result.get("summary", "No summary provided.")
            root_cause = result.get("root_cause", {})
            rc_statement = root_cause.get("statement", "Unknown") if isinstance(root_cause, dict) else str(root_cause)
            confidence = root_cause.get("confidence", 0.0) if isinstance(root_cause, dict) else 0.0
            confidence_pct = f"{int(confidence * 100)}%" if isinstance(confidence, (int, float)) else str(confidence)
            severity = result.get("severity", incident.diagnosis.get("severity", "MEDIUM"))

            print(f"\nSummary:\n{summary}")
            print(f"\nRoot Cause:\n{rc_statement}")
            print(f"\nConfidence:\n{confidence_pct}")
            print(f"\nSeverity:\n{severity}")

            # Evidence
            print("\n" + "-" * 60)
            print("EVIDENCE")
            print("-" * 60)
            evidence_items = result.get("evidence", [])
            if evidence_items:
                for ev in evidence_items:
                    if isinstance(ev, dict):
                        stmt = ev.get("statement", "")
                        src = ev.get("source", "")
                        src_str = f" ({src})" if src else ""
                        print(f"✓ {stmt}{src_str}")
                    else:
                        print(f"✓ {ev}")
            else:
                for cf in result.get("confirmed_facts", []):
                    print(f"✓ {cf}")

            # Impact
            print("\n" + "-" * 60)
            print("IMPACT")
            print("-" * 60)
            impact = result.get("impact", {})
            imp_stmt = impact.get("statement", "Impact unknown") if isinstance(impact, dict) else str(impact)
            print(imp_stmt)

            # Recommendations
            print("\n" + "-" * 60)
            print("RECOMMENDATIONS")
            print("-" * 60)
            recs = result.get("recommendations", [])
            if recs:
                for idx, r in enumerate(recs, 1):
                    if isinstance(r, dict):
                        act = r.get("action", "")
                        pri = r.get("priority", "MEDIUM")
                        print(f"{idx}. [{pri}] {act}")
                    else:
                        print(f"{idx}. {r}")
            else:
                print("No immediate recommendations.")

            # Unknowns / Next Checks
            unknowns = result.get("unknowns", [])
            if unknowns:
                print("\n" + "-" * 60)
                print("UNKNOWN")
                print("-" * 60)
                for u in unknowns:
                    print(f"• {u}")

            next_checks = result.get("next_checks", [])
            if next_checks:
                print("\n" + "-" * 60)
                print("NEXT CHECKS")
                print("-" * 60)
                for nc in next_checks:
                    print(f"• {nc}")

            usage = ai_data.get("usage", {})
            if usage:
                cost = usage.get("estimated_cost_usd", 0.0)
                dur = usage.get("request_duration_ms", 0.0)
                print(f"\n[AI Usage: {usage.get('total_tokens', 0)} tokens, {dur}ms, EST ${cost:.6f}]")

        else:
            err_msg = ai_data.get("error_message") or "AI provider not available or disabled."
            print(f"\nStatus:\n{status}")
            print(f"\nReason:\n{err_msg}")

        print("=" * 60 + "\n")
