import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ResourceRef:
    kind: str
    name: str
    namespace: str
    uid: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Incident:
    incident_id: str
    status: str  # "OPEN", "RESOLVED"
    resource: ResourceRef
    category: str  # e.g., "ImagePullFailure", "CrashLoopBackOff", "OOMKilled"
    current_state: str
    occurrences: int = 1
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    last_seen: str = field(default_factory=utc_now_iso)
    resolved_at: Optional[str] = None
    state_history: List[Union[str, Dict[str, Any]]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    diagnosis: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    investigation: Dict[str, Any] = field(default_factory=dict)
    identity_key: str = ""
    last_canonical_state: str = ""
    ai_analysis: Optional[Dict[str, Any]] = None
    ai_status: str = "NOT_ANALYZED"
    ai_updated_at: Optional[str] = None

    def __post_init__(self):
        if not self.identity_key:
            self.identity_key = self.compute_identity_key(
                self.resource.namespace,
                self.resource.kind,
                self.resource.uid or self.resource.name,
                self.category,
            )

    @staticmethod
    def normalize_state_history_entry(entry: Any, default_reason: Optional[str] = None) -> Dict[str, Any]:
        now_iso = utc_now_iso()
        if isinstance(entry, dict):
            st = entry.get("state") or entry.get("reason") or default_reason or "Unknown"
            rs = entry.get("reason") or entry.get("state") or default_reason or "Unknown"
            ts = entry.get("timestamp") or now_iso
            return {"state": st, "timestamp": ts, "reason": rs}
        st_str = str(entry)
        rs_str = default_reason or st_str
        return {"state": st_str, "timestamp": now_iso, "reason": rs_str}

    @staticmethod
    def compute_identity_key(namespace: str, kind: str, uid_or_name: str, category: str) -> str:
        """
        Creates a stable deduplication identity key based on:
        namespace + kind + (uid or name) + category.
        This prevents creating multiple incidents for state shifts like ErrImagePull -> ImagePullBackOff.
        """
        # Map related categories to a canonical category if needed
        canonical_cat = category
        if category in ["ErrImagePull", "ImagePullBackOff", "InvalidImageName"]:
            canonical_cat = "ImagePullFailure"
        elif category in ["CrashLoopBackOff", "Error", "RunContainerError"]:
            canonical_cat = "CrashLoop"
        elif category in ["CreateContainerConfigError", "CreateContainerError"]:
            canonical_cat = "ContainerConfigError"

        return f"{namespace}:{kind}:{uid_or_name}:{canonical_cat}"

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "incident_id": self.incident_id,
            "status": self.status,
            "resource": self.resource.to_dict() if isinstance(self.resource, ResourceRef) else self.resource,
            "category": self.category,
            "current_state": self.current_state,
            "occurrences": self.occurrences,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_seen": self.last_seen,
            "resolved_at": self.resolved_at,
            "state_history": self.state_history,
            "evidence": self.evidence,
            "diagnosis": self.diagnosis,
            "recommendations": self.recommendations,
            "investigation": self.investigation,
            "identity_key": self.identity_key,
            "last_canonical_state": self.last_canonical_state,
            "ai_analysis": self.ai_analysis,
            "ai_status": self.ai_status,
            "ai_updated_at": self.ai_updated_at,
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Incident":
        res_data = data.get("resource", {})
        res = ResourceRef(
            kind=res_data.get("kind", "Pod"),
            name=res_data.get("name", "unknown"),
            namespace=res_data.get("namespace", "default"),
            uid=res_data.get("uid", ""),
        )
        incident = cls(
            incident_id=data.get("incident_id", "INC-0000"),
            status=data.get("status", "OPEN"),
            resource=res,
            category=data.get("category", "Unknown"),
            current_state=data.get("current_state", "Unknown"),
            occurrences=data.get("occurrences", 1),
            created_at=data.get("created_at", utc_now_iso()),
            updated_at=data.get("updated_at", utc_now_iso()),
            last_seen=data.get("last_seen", utc_now_iso()),
            resolved_at=data.get("resolved_at"),
            state_history=data.get("state_history", []),
            evidence=data.get("evidence", []),
            diagnosis=data.get("diagnosis", {}),
            recommendations=data.get("recommendations", []),
            investigation=data.get("investigation", {}),
            identity_key=data.get("identity_key", ""),
            last_canonical_state=data.get("last_canonical_state", ""),
            ai_analysis=data.get("ai_analysis"),
            ai_status=data.get("ai_status", "NOT_ANALYZED"),
            ai_updated_at=data.get("ai_updated_at"),
        )
        return incident
