import os
import pytest

from app.incidents.models import Incident, ResourceRef
from app.remediation.catalog import SafeActionCatalog
from app.remediation.engine import RemediationEngine
from app.remediation.models import ActionType, ApprovalStatus, ExecutionStatus, RemediationPolicy, VerificationStatus
from app.remediation.store import RemediationStore


@pytest.fixture
def temp_remediation_store(tmp_path):
    plan_file = str(tmp_path / "remediations.json")
    audit_file = str(tmp_path / "audit.json")
    return RemediationStore(filepath=plan_file, audit_filepath=audit_file)


@pytest.fixture
def sample_incident():
    res = ResourceRef(kind="Pod", name="payment-processor-79d8b8584f-x2k9l", namespace="payments", uid="uid-pay-proc-882194")
    return Incident(
        incident_id="INC-0842",
        status="OPEN",
        resource=res,
        category="OOMKilled",
        current_state="OOMKilled",
        diagnosis={
            "root_cause": "Container exceeded memory limit of 512Mi",
            "mitigation_command": "kubectl set resources deployment/payment-processor -n payments --limits=memory=1Gi,cpu=500m",
        },
        recommendations=["Increase container memory limit in Deployment spec from 512Mi to 1Gi."],
    )


def test_allowlist_validation():
    # Valid allowlisted action
    allowed, risk, reason = SafeActionCatalog.is_action_allowlisted(ActionType.ROLLOUT_RESTART, target_kind="Deployment")
    assert allowed is True
    assert risk == "LOW"

    # Forbidden shell command injection attempt
    allowed_cmd, risk_cmd, reason_cmd = SafeActionCatalog.is_action_allowlisted(
        ActionType.ROLLOUT_RESTART, command_str="rm -rf / --no-preserve-root", target_kind="Deployment font"
    )
    assert allowed_cmd is False
    assert risk_cmd == "HIGH"
    assert "Forbidden" in reason_cmd or "not supported" in reason_cmd


def test_remediation_plan_creation_and_dry_run(temp_remediation_store, sample_incident):
    engine = RemediationEngine(store=temp_remediation_store, cluster_id="skyops-cluster-prod-us")

    plan = engine.create_plan_from_incident(sample_incident)
    assert plan.incident_id == "INC-0842"
    assert plan.cluster_id == "skyops-cluster-prod-us"
    assert plan.action_type == ActionType.RESOURCE_ADJUSTMENT
    assert plan.approval_status == ApprovalStatus.AWAITING_APPROVAL

    # Dry run
    passed, dry_res = engine.dry_run(plan.remediation_id)
    assert passed is True
    assert dry_res["passed"] is True
    assert "resource limits" in dry_res["expected_effect"].lower() or "validation succeeded" in dry_res["message"].lower()


def test_human_approval_workflow(temp_remediation_store, sample_incident):
    engine = RemediationEngine(store=temp_remediation_store, cluster_id="skyops-cluster-prod-us")
    plan = engine.create_plan_from_incident(sample_incident)

    # Execution without approval should be BLOCKED
    success, exec_res = engine.execute(plan.remediation_id, incident=sample_incident)
    assert success is False
    assert exec_res["status"] == "BLOCKED"
    assert "human approval required" in exec_res["reason"].lower()

    # Operator approves
    approved_plan = engine.approve(plan.remediation_id, approved_by="sre-operator@company.com")
    assert approved_plan.approval_status == ApprovalStatus.APPROVED
    assert approved_plan.approved_by == "sre-operator@company.com"


def test_multi_cluster_isolation_precondition(temp_remediation_store, sample_incident):
    engine = RemediationEngine(store=temp_remediation_store, cluster_id="skyops-cluster-staging-eu")
    plan = engine.create_plan_from_incident(sample_incident)  # Cluster ID = skyops-cluster-staging-eu
    plan.cluster_id = "skyops-cluster-prod-us"  # Mismatch cluster!
    temp_remediation_store.save_plan(plan)

    engine.approve(plan.remediation_id)
    success, exec_res = engine.execute(plan.remediation_id, incident=sample_incident)
    assert success is False
    assert exec_res["status"] == "BLOCKED"
    assert "wrong cluster id" in exec_res["reason"].lower()


def test_execution_verification_and_audit(temp_remediation_store, sample_incident):
    engine = RemediationEngine(store=temp_remediation_store, cluster_id="skyops-cluster-prod-us")
    plan = engine.create_plan_from_incident(sample_incident)
    engine.approve(plan.remediation_id)

    # Execute
    success, exec_res = engine.execute(plan.remediation_id, incident=sample_incident)
    assert success is True
    assert exec_res["status"] == "EXECUTED"

    # Verify Incident state updated to RESOLVED ONLY after verification
    assert sample_incident.status == "RESOLVED"

    # Verify Audit Record created
    audits = temp_remediation_store.list_audit_records()
    assert len(audits) == 1
    assert audits[0].remediation_id == plan.remediation_id
    assert audits[0].verification_status == VerificationStatus.SUCCESS


def test_idempotency_prevents_duplicate_execution(temp_remediation_store, sample_incident):
    engine = RemediationEngine(store=temp_remediation_store, cluster_id="skyops-cluster-prod-us")
    plan = engine.create_plan_from_incident(sample_incident)
    engine.approve(plan.remediation_id)

    # First execution
    success_1, exec_res_1 = engine.execute(plan.remediation_id, incident=sample_incident)
    assert success_1 is True

    # Second execution attempt (duplicate)
    success_2, exec_res_2 = engine.execute(plan.remediation_id, incident=sample_incident)
    assert success_2 is True
    assert exec_res_2["status"] == "ALREADY_EXECUTED"
    assert "previously executed" in exec_res_2["message"].lower()
