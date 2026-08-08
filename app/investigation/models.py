from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class InvestigationResult:
    """
    Complete evidence, relationships, and findings collected for an incident investigation.
    """
    incident_id: str
    target: Dict[str, Any] = field(default_factory=dict)
    pod: Dict[str, Any] = field(default_factory=dict)
    controllers: List[Dict[str, Any]] = field(default_factory=list)
    deployment: Dict[str, Any] = field(default_factory=dict)
    replicaset: Dict[str, Any] = field(default_factory=dict)
    services: List[Dict[str, Any]] = field(default_factory=list)
    service: Dict[str, Any] = field(default_factory=dict)
    endpoints: List[Dict[str, Any]] = field(default_factory=list)
    node: Dict[str, Any] = field(default_factory=dict)
    storage: Dict[str, Any] = field(default_factory=dict)
    configmaps: List[Dict[str, Any]] = field(default_factory=list)
    secrets: List[Dict[str, Any]] = field(default_factory=list)  # NEVER secret data/values
    events: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, str]] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    collector_status: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvestigationResult":
        return cls(
            incident_id=data.get("incident_id", "UNKNOWN"),
            target=data.get("target", {}),
            pod=data.get("pod", {}),
            controllers=data.get("controllers", []),
            deployment=data.get("deployment", {}),
            replicaset=data.get("replicaset", {}),
            services=data.get("services", []),
            service=data.get("service", {}),
            endpoints=data.get("endpoints", []),
            node=data.get("node", {}),
            storage=data.get("storage", {}),
            configmaps=data.get("configmaps", []),
            secrets=data.get("secrets", []),
            events=data.get("events", []),
            relationships=data.get("relationships", []),
            findings=data.get("findings", []),
            collector_status=data.get("collector_status", {}),
        )
