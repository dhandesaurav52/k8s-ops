from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RootCause:
    statement: str
    confidence: float  # 0.0 to 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceItem:
    statement: str
    source: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Impact:
    level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RecommendationItem:
    priority: str  # "HIGH", "MEDIUM", "LOW"
    action: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AIIncidentAnalysis:
    summary: str
    incident_type: str
    severity: str
    root_cause: RootCause
    evidence: List[EvidenceItem]
    impact: Impact
    recommendations: List[RecommendationItem]
    confirmed_facts: List[str] = field(default_factory=list)
    likely_causes: List[str] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    next_checks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "incident_type": self.incident_type,
            "severity": self.severity,
            "root_cause": self.root_cause.to_dict() if isinstance(self.root_cause, RootCause) else self.root_cause,
            "evidence": [e.to_dict() if isinstance(e, EvidenceItem) else e for e in self.evidence],
            "impact": self.impact.to_dict() if isinstance(self.impact, Impact) else self.impact,
            "recommendations": [r.to_dict() if isinstance(r, RecommendationItem) else r for r in self.recommendations],
            "confirmed_facts": self.confirmed_facts,
            "likely_causes": self.likely_causes,
            "unknowns": self.unknowns,
            "next_checks": self.next_checks,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIIncidentAnalysis":
        rc = data.get("root_cause", {})
        root_cause = RootCause(
            statement=rc.get("statement", "Unknown root cause"),
            confidence=float(rc.get("confidence", 0.0))
        ) if isinstance(rc, dict) else rc

        ev_list = []
        for item in data.get("evidence", []):
            if isinstance(item, dict):
                ev_list.append(EvidenceItem(
                    statement=item.get("statement", ""),
                    source=item.get("source", "unknown")
                ))
            elif isinstance(item, str):
                ev_list.append(EvidenceItem(statement=item, source="general"))

        imp = data.get("impact", {})
        impact = Impact(
            level=imp.get("level", "MEDIUM"),
            statement=imp.get("statement", "")
        ) if isinstance(imp, dict) else imp

        rec_list = []
        for rec in data.get("recommendations", []):
            if isinstance(rec, dict):
                rec_list.append(RecommendationItem(
                    priority=rec.get("priority", "MEDIUM"),
                    action=rec.get("action", "")
                ))
            elif isinstance(rec, str):
                rec_list.append(RecommendationItem(priority="MEDIUM", action=rec))

        return cls(
            summary=data.get("summary", ""),
            incident_type=data.get("incident_type", "Unknown"),
            severity=data.get("severity", "MEDIUM"),
            root_cause=root_cause,
            evidence=ev_list,
            impact=impact,
            recommendations=rec_list,
            confirmed_facts=data.get("confirmed_facts", []),
            likely_causes=data.get("likely_causes", []),
            unknowns=data.get("unknowns", []),
            next_checks=data.get("next_checks", []),
        )


@dataclass
class AIUsage:
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    request_duration_ms: float
    estimated_cost_usd: float
    timestamp: str = field(default_factory=utc_now_iso)
    incident_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def calculate_cost(
        cls,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: float,
        incident_id: str,
        input_cost_per_m: float = 0.10,
        output_cost_per_m: float = 0.40,
    ) -> "AIUsage":
        total_tokens = input_tokens + output_tokens
        cost = (input_tokens / 1_000_000.0) * input_cost_per_m + (output_tokens / 1_000_000.0) * output_cost_per_m
        return cls(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            request_duration_ms=round(duration_ms, 2),
            estimated_cost_usd=round(cost, 6),
            incident_id=incident_id,
        )


@dataclass
class AIAnalysisResponse:
    provider: str
    model: str
    generated_at: str
    analysis_version: int
    status: str  # "SUCCESS", "FAILED", "DISABLED", "UNAVAILABLE", "FAILED_TO_PARSE"
    result: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "generated_at": self.generated_at,
            "analysis_version": self.analysis_version,
            "status": self.status,
            "result": self.result,
            "usage": self.usage,
            "error_message": self.error_message,
        }
