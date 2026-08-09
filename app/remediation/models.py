import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ActionType:
    ROLLOUT_RESTART = "ROLLOUT_RESTART"
    SCALE_WORKLOAD = "SCALE_WORKLOAD"
    ROLLBACK_WORKLOAD = "ROLLBACK_WORKLOAD"
    RESOURCE_ADJUSTMENT = "RESOURCE_ADJUSTMENT"
    UNSUPPORTED = "UNSUPPORTED"


class ApprovalStatus:
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ExecutionStatus:
    NOT_STARTED = "NOT_STARTED"
    DRY_RUN_PASSED = "DRY_RUN_PASSED"
    DRY_RUN_FAILED = "DRY_RUN_FAILED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    ALREADY_EXECUTED = "ALREADY_EXECUTED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class VerificationStatus:
    NOT_STARTED = "NOT_STARTED"
    VERIFYING = "VERIFYING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


@dataclass
class RemediationPlan:
    remediation_id: str
    incident_id: str
    cluster_id: str
    target_kind: str
    target_name: str
    namespace: str
    action_type: str
    command_action: str
    reason: str
    target_uid: str = ""
    action_params: Dict[str, Any] = field(default_factory=dict)
    evidence_references: List[str] = field(default_factory=list)
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH
    approval_status: str = ApprovalStatus.AWAITING_APPROVAL
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    rejected_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    execution_status: str = ExecutionStatus.NOT_STARTED
    dry_run_result: Optional[Dict[str, Any]] = None
    execution_result: Optional[Dict[str, Any]] = None
    verification_status: str = VerificationStatus.NOT_STARTED
    verification_result: Optional[Dict[str, Any]] = None
    rollback_status: Optional[str] = "NOT_AVAILABLE"  # NOT_AVAILABLE, AVAILABLE, ROLLING_BACK, ROLLED_BACK, ROLLBACK_FAILED
    rollback_result: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=utc_now_iso)
    executed_at: Optional[str] = None
    completed_at: Optional[str] = None
    failure_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RemediationPlan":
        return cls(
            remediation_id=data.get("remediation_id", f"REM-{uuid.uuid4().hex[:6].upper()}"),
            incident_id=data.get("incident_id", "INC-0000"),
            cluster_id=data.get("cluster_id", "skyops-cluster-default"),
            target_kind=data.get("target_kind", "Deployment"),
            target_name=data.get("target_name", "unknown"),
            namespace=data.get("namespace", "default"),
            target_uid=data.get("target_uid", ""),
            action_type=data.get("action_type", ActionType.ROLLOUT_RESTART),
            command_action=data.get("command_action", ""),
            action_params=data.get("action_params", {}),
            reason=data.get("reason", ""),
            evidence_references=data.get("evidence_references", []),
            risk_level=data.get("risk_level", "LOW"),
            approval_status=data.get("approval_status", ApprovalStatus.AWAITING_APPROVAL),
            approved_by=data.get("approved_by"),
            approved_at=data.get("approved_at"),
            rejected_at=data.get("rejected_at"),
            rejection_reason=data.get("rejection_reason"),
            execution_status=data.get("execution_status", ExecutionStatus.NOT_STARTED),
            dry_run_result=data.get("dry_run_result"),
            execution_result=data.get("execution_result"),
            verification_status=data.get("verification_status", VerificationStatus.NOT_STARTED),
            verification_result=data.get("verification_result"),
            rollback_status=data.get("rollback_status", "NOT_AVAILABLE"),
            rollback_result=data.get("rollback_result"),
            created_at=data.get("created_at", utc_now_iso()),
            executed_at=data.get("executed_at"),
            completed_at=data.get("completed_at"),
            failure_reason=data.get("failure_reason"),
        )


@dataclass
class RemediationPolicy:
    policy_id: str = "default-policy"
    cluster_id: str = "ALL"
    environment: str = "production"
    allowed_actions: List[str] = field(
        default_factory=lambda: [
            ActionType.ROLLOUT_RESTART,
            ActionType.SCALE_WORKLOAD,
            ActionType.ROLLBACK_WORKLOAD,
            ActionType.RESOURCE_ADJUSTMENT,
        ]
    )
    require_human_approval: bool = True  # Safe default: Always require human approval
    max_replicas: int = 10
    min_replicas: int = 1
    max_remediations_per_incident: int = 1
    max_remediations_per_cluster_hour: int = 10
    cooldown_seconds: int = 300
    allow_auto_rollback: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RemediationPolicy":
        return cls(
            policy_id=data.get("policy_id", "default-policy"),
            cluster_id=data.get("cluster_id", "ALL"),
            environment=data.get("environment", "production"),
            allowed_actions=data.get(
                "allowed_actions",
                [
                    ActionType.ROLLOUT_RESTART,
                    ActionType.SCALE_WORKLOAD,
                    ActionType.ROLLBACK_WORKLOAD,
                    ActionType.RESOURCE_ADJUSTMENT,
                ],
            ),
            require_human_approval=data.get("require_human_approval", True),
            max_replicas=data.get("max_replicas", 10),
            min_replicas=data.get("min_replicas", 1),
            max_remediations_per_incident=data.get("max_remediations_per_incident", 1),
            max_remediations_per_cluster_hour=data.get("max_remediations_per_cluster_hour", 10),
            cooldown_seconds=data.get("cooldown_seconds", 300),
            allow_auto_rollback=data.get("allow_auto_rollback", False),
        )


@dataclass
class AuditRecord:
    audit_id: str
    remediation_id: str
    incident_id: str
    cluster_id: str
    namespace: str
    target_resource: str
    action_type: str
    approved_by: str
    approved_at: str
    dry_run_passed: bool
    execution_status: str
    verification_status: str
    rollback_status: Optional[str] = "NOT_AVAILABLE"
    failure_reason: Optional[str] = None
    timestamp: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
