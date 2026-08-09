from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EvidenceItem:
    """
    Structured evidence item for signal correlation and timeline building.
    Represents a discrete, observable fact in the Kubernetes cluster.
    """
    evidence_id: str
    incident_id: str
    source: str  # KUBERNETES_EVENT, CONTAINER_STATE, POD_STATE, LOG, METRIC, NODE_STATE, WORKLOAD_STATE, STATE_TRANSITION
    resource: str  # e.g., "pod/payment-api-7f8...", "node/gke-node-1"
    timestamp: str  # ISO string timestamp
    signal_type: str  # e.g., "OOMKilled", "MemoryThresholdExceeded", "EventWarning", "StateShift"
    observation: str  # Human-readable observation description
    relevance: str = "HIGH"  # HIGH, MEDIUM, LOW
    raw_reference: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "incident_id": self.incident_id,
            "source": self.source,
            "resource": self.resource,
            "timestamp": self.timestamp,
            "signal_type": self.signal_type,
            "observation": self.observation,
            "relevance": self.relevance,
            "raw_reference": self.raw_reference or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceItem":
        return cls(
            evidence_id=data.get("evidence_id", "EVD-UNK"),
            incident_id=data.get("incident_id", ""),
            source=data.get("source", "UNKNOWN"),
            resource=data.get("resource", "unknown"),
            timestamp=data.get("timestamp", utc_now_iso()),
            signal_type=data.get("signal_type", "UnknownSignal"),
            observation=data.get("observation", ""),
            relevance=data.get("relevance", "HIGH"),
            raw_reference=data.get("raw_reference"),
        )


@dataclass
class BlastRadius:
    """
    Calculated impact scope of a Kubernetes incident based on topology and service health.
    """
    scope_level: str  # CONTAINER, POD, WORKLOAD, NAMESPACE, NODE, CLUSTER
    summary: str
    impacted_resources: List[Dict[str, Any]] = field(default_factory=list)
    workload_status: Dict[str, Any] = field(default_factory=dict)
    service_status: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope_level": self.scope_level,
            "summary": self.summary,
            "impacted_resources": self.impacted_resources,
            "workload_status": self.workload_status,
            "service_status": self.service_status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BlastRadius":
        return cls(
            scope_level=data.get("scope_level", "POD"),
            summary=data.get("summary", "Impact scope calculated"),
            impacted_resources=data.get("impacted_resources", []),
            workload_status=data.get("workload_status", {}),
            service_status=data.get("service_status", []),
        )


@dataclass
class RelatedIncident:
    """
    Summary of a historically or temporally related incident.
    """
    incident_id: str
    resource_name: str
    namespace: str
    category: str
    relationship_type: str  # SAME_RESOURCE, RELATED_RESOURCE, SIMILAR_INCIDENT
    created_at: str
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "resource_name": self.resource_name,
            "namespace": self.namespace,
            "category": self.category,
            "relationship_type": self.relationship_type,
            "created_at": self.created_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RelatedIncident":
        return cls(
            incident_id=data.get("incident_id", ""),
            resource_name=data.get("resource_name", ""),
            namespace=data.get("namespace", "default"),
            category=data.get("category", "Unknown"),
            relationship_type=data.get("relationship_type", "SIMILAR_INCIDENT"),
            created_at=data.get("created_at", utc_now_iso()),
            status=data.get("status", "OPEN"),
        )


@dataclass
class RootCauseAnalysis:
    """
    Deterministic evidence-based root cause diagnosis and score.
    """
    candidate_root_cause: str
    confidence_score: int  # 0 to 100
    confidence_level: str  # HIGH, MEDIUM, LOW
    confidence_reasoning: str
    supporting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    contradicting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    impacted_resources: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_root_cause": self.candidate_root_cause,
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level,
            "confidence_reasoning": self.confidence_reasoning,
            "supporting_evidence": self.supporting_evidence,
            "contradicting_evidence": self.contradicting_evidence,
            "impacted_resources": self.impacted_resources,
            "recommended_actions": self.recommended_actions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RootCauseAnalysis":
        return cls(
            candidate_root_cause=data.get("candidate_root_cause", "Unknown failure cause"),
            confidence_score=int(data.get("confidence_score", 0)),
            confidence_level=data.get("confidence_level", "LOW"),
            confidence_reasoning=data.get("confidence_reasoning", ""),
            supporting_evidence=data.get("supporting_evidence", []),
            contradicting_evidence=data.get("contradicting_evidence", []),
            impacted_resources=data.get("impacted_resources", []),
            recommended_actions=data.get("recommended_actions", []),
        )


@dataclass
class CorrelationResult:
    """
    Full output payload of the CorrelationEngine.
    """
    incident_id: str
    evidence_timeline: List[Dict[str, Any]] = field(default_factory=list)
    root_cause_analysis: Dict[str, Any] = field(default_factory=dict)
    blast_radius: Dict[str, Any] = field(default_factory=dict)
    related_incidents: List[Dict[str, Any]] = field(default_factory=list)
    correlation_window_minutes: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "evidence_timeline": self.evidence_timeline,
            "root_cause_analysis": self.root_cause_analysis,
            "blast_radius": self.blast_radius,
            "related_incidents": self.related_incidents,
            "correlation_window_minutes": self.correlation_window_minutes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CorrelationResult":
        return cls(
            incident_id=data.get("incident_id", ""),
            evidence_timeline=data.get("evidence_timeline", []),
            root_cause_analysis=data.get("root_cause_analysis", {}),
            blast_radius=data.get("blast_radius", {}),
            related_incidents=data.get("related_incidents", []),
            correlation_window_minutes=data.get("correlation_window_minutes", 5),
        )
