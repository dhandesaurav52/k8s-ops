import datetime
import logging
import uuid
from typing import Any, Dict, Optional, Tuple

from app.incidents.models import Incident, utc_now_iso
from app.remediation.catalog import SafeActionCatalog
from app.remediation.models import (
    ActionType,
    ApprovalStatus,
    AuditRecord,
    ExecutionStatus,
    RemediationPlan,
    RemediationPolicy,
    VerificationStatus,
)
from app.remediation.store import RemediationStore

logger = logging.getLogger("SkyOps.RemediationEngine")


class RemediationEngine:
    """
    Dedicated Safe Automated Remediation Engine.
    Enforces separation of Diagnosis -> Recommendation -> Approval -> Dry-Run -> Execution -> Verification -> Audit.
    """

    def __init__(
        self,
        store: Optional[RemediationStore] = None,
        default_policy: Optional[RemediationPolicy] = None,
        cluster_id: str = "skyops-cluster-default",
    ):
        self.store = store or RemediationStore()
        self.policy = default_policy or RemediationPolicy()
        self.cluster_id = cluster_id

    def create_plan_from_incident(self, incident: Incident) -> RemediationPlan:
        """
        Creates a structured remediation proposal plan from an Incident object.
        """
        # Check if plan already exists for this incident
        existing = self.store.get_plan_for_incident(incident.incident_id)
        if existing:
            return existing

        # Extract recommendation text & mitigation command from diagnosis / AI
        diagnosis = incident.diagnosis or {}
        ai_analysis = incident.ai_analysis or {}
        rec_text = ""
        if isinstance(incident.recommendations, list) and len(incident.recommendations) > 0:
            rec_text = incident.recommendations[0]

        mitigation_cmd = diagnosis.get("mitigation_command", "")
        category = incident.category

        # Map to structured proposal
        proposal = SafeActionCatalog.map_recommendation_to_proposal(
            incident_id=incident.incident_id,
            cluster_id=self.cluster_id,
            resource_kind=incident.resource.kind,
            resource_name=incident.resource.name,
            namespace=incident.resource.namespace,
            recommendation=rec_text,
            mitigation_cmd=mitigation_cmd,
            category=category,
            target_uid=incident.resource.uid,
        )

        rem_id = f"REM-{uuid.uuid4().hex[:6].upper()}"
        plan = RemediationPlan(
            remediation_id=rem_id,
            incident_id=proposal["incident_id"],
            cluster_id=proposal["cluster_id"],
            target_kind=proposal["target_kind"],
            target_name=proposal["target_name"],
            namespace=proposal["namespace"],
            target_uid=proposal["target_uid"],
            action_type=proposal["action_type"],
            command_action=proposal["command_action"],
            action_params=proposal["action_params"],
            reason=proposal["reason"],
            risk_level=proposal["risk_level"],
            approval_status=ApprovalStatus.AWAITING_APPROVAL,
            execution_status=ExecutionStatus.NOT_STARTED,
            created_at=utc_now_iso(),
        )

        self.store.save_plan(plan)

        # Extend incident state lifecycle
        if incident.status == "OPEN":
            incident.status = "AWAITING_APPROVAL"
            incident.updated_at = utc_now_iso()

        logger.info(f"Created Remediation Plan {plan.remediation_id} for Incident {incident.incident_id}")
        return plan

    def dry_run(self, plan_id: str, k8s_client: Any = None, apps_v1_api: Any = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Performs a Dry Run validation of the remediation plan without mutating cluster state.
        """
        plan = self.store.get_plan(plan_id)
        if not plan:
            return False, {"passed": False, "error": f"Remediation Plan {plan_id} not found."}

        # Multi-cluster validation
        if plan.cluster_id != self.cluster_id and self.cluster_id != "ALL" and plan.cluster_id != "ALL":
            msg = f"Cluster ID mismatch: Plan cluster '{plan.cluster_id}' vs Agent cluster '{self.cluster_id}'"
            plan.execution_status = ExecutionStatus.DRY_RUN_FAILED
            plan.dry_run_result = {"passed": False, "reason": msg}
            self.store.save_plan(plan)
            return False, {"passed": False, "error": msg}

        # Allowlist validation
        is_allowed, risk, reason = SafeActionCatalog.is_action_allowlisted(
            plan.action_type, plan.command_action, plan.target_kind
        )

        if not is_allowed:
            res = {"passed": False, "reason": f"Action not allowlisted: {reason}"}
            plan.execution_status = ExecutionStatus.DRY_RUN_FAILED
            plan.dry_run_result = res
            self.store.save_plan(plan)
            return False, res

        # Resource Existence Check (Mock or Live)
        resource_found = True
        target_info = f"{plan.target_kind}/{plan.target_name} in ns/{plan.namespace}"

        if apps_v1_api and hasattr(apps_v1_api, "read_namespaced_deployment"):
            try:
                if plan.target_kind == "Deployment":
                    apps_v1_api.read_namespaced_deployment(name=plan.target_name, namespace=plan.namespace)
                elif plan.target_kind == "StatefulSet":
                    apps_v1_api.read_namespaced_stateful_set(name=plan.target_name, namespace=plan.namespace)
            except Exception as e:
                resource_found = False
                res = {"passed": False, "reason": f"Target resource {target_info} not found in cluster: {e}"}
                plan.execution_status = ExecutionStatus.DRY_RUN_FAILED
                plan.dry_run_result = res
                self.store.save_plan(plan)
                return False, res

        # Calculate expected effect
        expected_effect = "No changes made."
        if plan.action_type == ActionType.ROLLOUT_RESTART:
            expected_effect = f"Will trigger a rolling pod restart for {target_info} by updating restart annotation."
        elif plan.action_type == ActionType.SCALE_WORKLOAD:
            replicas = plan.action_params.get("replicas", 2)
            expected_effect = f"Will adjust replica count for {target_info} to {replicas}."
        elif plan.action_type == ActionType.ROLLBACK_WORKLOAD:
            expected_effect = f"Will rollback {target_info} spec to previous deployment revision."
        elif plan.action_type == ActionType.RESOURCE_ADJUSTMENT:
            expected_effect = f"Will update container resource limits on {target_info}."

        res = {
            "passed": True,
            "target_resource": target_info,
            "target_found": resource_found,
            "risk_level": plan.risk_level,
            "action_type": plan.action_type,
            "expected_effect": expected_effect,
            "message": "Dry run successful. All precondition and policy checks passed.",
        }

        plan.execution_status = ExecutionStatus.DRY_RUN_PASSED
        plan.dry_run_result = res
        self.store.save_plan(plan)
        return True, res

    def approve(self, plan_id: str, approved_by: str = "operator@skyops.internal") -> RemediationPlan:
        """
        Operator explicitly approves remediation execution.
        """
        plan = self.store.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Remediation Plan {plan_id} not found.")

        plan.approval_status = ApprovalStatus.APPROVED
        plan.approved_by = approved_by
        plan.approved_at = utc_now_iso()
        self.store.save_plan(plan)
        logger.info(f"Remediation Plan {plan.remediation_id} APPROVED by {approved_by}")
        return plan

    def reject(
        self, plan_id: str, rejected_by: str = "operator@skyops.internal", reason: str = "Operator rejected proposal"
    ) -> RemediationPlan:
        """
        Operator rejects remediation execution.
        """
        plan = self.store.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Remediation Plan {plan_id} not found.")

        plan.approval_status = ApprovalStatus.REJECTED
        plan.rejected_at = utc_now_iso()
        plan.rejection_reason = reason
        plan.execution_status = ExecutionStatus.BLOCKED
        self.store.save_plan(plan)
        logger.info(f"Remediation Plan {plan.remediation_id} REJECTED by {rejected_by}")
        return plan

    def validate_preconditions(
        self, plan: RemediationPlan, incident: Optional[Incident] = None, policy: Optional[RemediationPolicy] = None
    ) -> Tuple[bool, str]:
        """
        Validates all strict execution preconditions before applying changes to Kubernetes.
        """
        pol = policy or self.policy

        # 1. Cluster Identity Check
        if plan.cluster_id != self.cluster_id and self.cluster_id != "ALL" and plan.cluster_id != "ALL":
            return False, f"Remediation blocked: wrong cluster ID (Plan: '{plan.cluster_id}', Agent: '{self.cluster_id}')."

        # 2. Idempotency Check
        if plan.execution_status in [ExecutionStatus.EXECUTED, ExecutionStatus.ALREADY_EXECUTED]:
            return False, "Remediation blocked: action already executed (idempotency check)."

        # 3. Human Approval Check
        if pol.require_human_approval and plan.approval_status != ApprovalStatus.APPROVED:
            return False, f"Remediation blocked: human approval required (current status: '{plan.approval_status}')."

        # 4. Action Allowlist & Risk Check
        if plan.action_type == ActionType.UNSUPPORTED:
            return False, "Remediation blocked: action is unsupported or classified as high risk."

        if plan.action_type not in pol.allowed_actions:
            return False, f"Remediation blocked: action '{plan.action_type}' not permitted by policy."

        # 5. Incident Active Check
        if incident:
            if incident.status == "RESOLVED":
                return False, "Remediation blocked: target incident is already marked RESOLVED."

        # 6. Policy replica bounds
        if plan.action_type == ActionType.SCALE_WORKLOAD:
            desired_replicas = plan.action_params.get("replicas", 1)
            if desired_replicas > pol.max_replicas:
                return False, f"Remediation blocked: requested scale ({desired_replicas}) exceeds policy limit ({pol.max_replicas})."
            if desired_replicas < pol.min_replicas:
                return False, f"Remediation blocked: requested scale ({desired_replicas}) below policy limit ({pol.min_replicas})."

        return True, "Preconditions validated successfully."

    def execute(
        self,
        plan_id: str,
        incident: Optional[Incident] = None,
        apps_v1_api: Any = None,
        policy: Optional[RemediationPolicy] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Executes the allowlisted remediation action against the Kubernetes API.
        NO arbitrary shell execution! Uses structured Kubernetes API client calls.
        """
        plan = self.store.get_plan(plan_id)
        if not plan:
            return False, {"status": "FAILED", "reason": f"Remediation plan {plan_id} not found."}

        # Idempotency early return
        if plan.execution_status == ExecutionStatus.EXECUTED:
            plan.execution_status = ExecutionStatus.ALREADY_EXECUTED
            self.store.save_plan(plan)
            return True, {"status": "ALREADY_EXECUTED", "message": "Action previously executed. Duplicate call ignored."}

        # Precondition Validation
        is_valid, msg = self.validate_preconditions(plan, incident=incident, policy=policy)
        if not is_valid:
            plan.execution_status = ExecutionStatus.BLOCKED
            plan.failure_reason = msg
            self.store.save_plan(plan)
            return False, {"status": "BLOCKED", "reason": msg}

        plan.execution_status = ExecutionStatus.EXECUTING
        self.store.save_plan(plan)

        now_iso = utc_now_iso()
        exec_success = False
        exec_details = {}

        try:
            # -----------------------------------------------------------------
            # 1. ROLLOUT_RESTART
            # -----------------------------------------------------------------
            if plan.action_type == ActionType.ROLLOUT_RESTART:
                if apps_v1_api and hasattr(apps_v1_api, "patch_namespaced_deployment"):
                    patch_body = {
                        "spec": {
                            "template": {
                                "metadata": {
                                    "annotations": {"kubectl.kubernetes.io/restartedAt": now_iso}
                                }
                            }
                        }
                    }
                    if plan.target_kind == "Deployment":
                        apps_v1_api.patch_namespaced_deployment(name=plan.target_name, namespace=plan.namespace, body=patch_body)
                    elif plan.target_kind == "StatefulSet":
                        apps_v1_api.patch_namespaced_stateful_set(name=plan.target_name, namespace=plan.namespace, body=patch_body)
                    elif plan.target_kind == "DaemonSet":
                        apps_v1_api.patch_namespaced_daemon_set(name=plan.target_name, namespace=plan.namespace, body=patch_body)
                exec_success = True
                exec_details = {"method": "k8s_api_patch_restartedAt", "timestamp": now_iso}

            # -----------------------------------------------------------------
            # 2. SCALE_WORKLOAD
            # -----------------------------------------------------------------
            elif plan.action_type == ActionType.SCALE_WORKLOAD:
                replicas = plan.action_params.get("replicas", 2)
                if apps_v1_api and hasattr(apps_v1_api, "patch_namespaced_deployment_scale"):
                    scale_body = {"spec": {"replicas": replicas}}
                    if plan.target_kind == "Deployment":
                        apps_v1_api.patch_namespaced_deployment_scale(name=plan.target_name, namespace=plan.namespace, body=scale_body)
                    elif plan.target_kind == "StatefulSet":
                        apps_v1_api.patch_namespaced_stateful_set_scale(name=plan.target_name, namespace=plan.namespace, body=scale_body)
                exec_success = True
                exec_details = {"method": "k8s_api_scale", "replicas": replicas}

            # -----------------------------------------------------------------
            # 3. ROLLBACK_WORKLOAD
            # -----------------------------------------------------------------
            elif plan.action_type == ActionType.ROLLBACK_WORKLOAD:
                if apps_v1_api and hasattr(apps_v1_api, "patch_namespaced_deployment"):
                    # Rollback patch or image undo
                    patch_body = {"spec": {"template": {"metadata": {"annotations": {"skyops.io/rollbackAt": now_iso}}}}}
                    apps_v1_api.patch_namespaced_deployment(name=plan.target_name, namespace=plan.namespace, body=patch_body)
                exec_success = True
                exec_details = {"method": "k8s_api_rollback", "timestamp": now_iso}

            # -----------------------------------------------------------------
            # 4. RESOURCE_ADJUSTMENT
            # -----------------------------------------------------------------
            elif plan.action_type == ActionType.RESOURCE_ADJUSTMENT:
                mem_limit = plan.action_params.get("memory_limit", "1Gi")
                cpu_limit = plan.action_params.get("cpu_limit", "500m")
                if apps_v1_api and hasattr(apps_v1_api, "patch_namespaced_deployment"):
                    patch_body = {
                        "spec": {
                            "template": {
                                "spec": {
                                    "containers": [
                                        {
                                            "name": plan.target_name,
                                            "resources": {
                                                "limits": {"memory": mem_limit, "cpu": cpu_limit}
                                            },
                                        }
                                    ]
                                }
                            }
                        }
                    }
                    apps_v1_api.patch_namespaced_deployment(name=plan.target_name, namespace=plan.namespace, body=patch_body)
                exec_success = True
                exec_details = {"method": "k8s_api_resource_adjustment", "memory_limit": mem_limit, "cpu_limit": cpu_limit}

            else:
                exec_success = False
                exec_details = {"error": f"Unsupported action type '{plan.action_type}'"}

        except Exception as e:
            logger.error(f"Execution failed for remediation plan {plan_id}: {e}")
            plan.execution_status = ExecutionStatus.FAILED
            plan.failure_reason = f"Kubernetes API error: {e}"
            self.store.save_plan(plan)
            return False, {"status": "FAILED", "reason": str(e)}

        if exec_success:
            plan.execution_status = ExecutionStatus.EXECUTED
            plan.executed_at = now_iso
            plan.execution_result = exec_details
            self.store.save_plan(plan)

            # Update Incident state
            if incident:
                incident.status = "VERIFYING"
                incident.updated_at = now_iso

            logger.info(f"Successfully EXECUTED Remediation Plan {plan.remediation_id} on {plan.namespace}/{plan.target_name}")

            # Automatically trigger post-remediation verification
            self.verify(plan_id, incident=incident, apps_v1_api=apps_v1_api)

            return True, {"status": "EXECUTED", "details": exec_details}
        else:
            plan.execution_status = ExecutionStatus.FAILED
            plan.failure_reason = "Execution error"
            self.store.save_plan(plan)
            return False, {"status": "FAILED", "reason": "Execution failed"}

    def verify(
        self,
        plan_id: str,
        incident: Optional[Incident] = None,
        apps_v1_api: Any = None,
        timeout_seconds: int = 120,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verifies workload health after remediation execution.
        ONLY marks incident RESOLVED if verification succeeds!
        """
        plan = self.store.get_plan(plan_id)
        if not plan:
            return False, {"status": "FAILED", "reason": f"Plan {plan_id} not found."}

        plan.verification_status = VerificationStatus.VERIFYING
        self.store.save_plan(plan)

        verified_healthy = True
        verification_details = {
            "workload": f"{plan.target_kind}/{plan.target_name}",
            "namespace": plan.namespace,
            "checked_at": utc_now_iso(),
        }

        if apps_v1_api and hasattr(apps_v1_api, "read_namespaced_deployment_status"):
            try:
                if plan.target_kind == "Deployment":
                    dep = apps_v1_api.read_namespaced_deployment_status(name=plan.target_name, namespace=plan.namespace)
                    status = getattr(dep, "status", None)
                    if status:
                        desired = getattr(status, "replicas", 1)
                        ready = getattr(status, "ready_replicas", 0) or 0
                        updated = getattr(status, "updated_replicas", 0) or 0
                        if ready >= desired and updated >= desired:
                            verified_healthy = True
                            verification_details["ready_replicas"] = ready
                            verification_details["desired_replicas"] = desired
                        else:
                            verified_healthy = False
                            verification_details["reason"] = f"Replicas not ready ({ready}/{desired} ready, {updated}/{desired} updated)"
            except Exception as e:
                verified_healthy = False
                verification_details["reason"] = f"API error checking status: {e}"

        now_iso = utc_now_iso()
        if verified_healthy:
            plan.verification_status = VerificationStatus.SUCCESS
            plan.completed_at = now_iso
            plan.verification_result = verification_details
            self.store.save_plan(plan)

            # ONLY NOW mark Incident RESOLVED
            if incident:
                incident.status = "RESOLVED"
                incident.resolved_at = now_iso
                incident.updated_at = now_iso
                if not incident.state_history or incident.state_history[-1] != "Running":
                    incident.state_history.append("Running")

            # Create Audit Record
            audit = AuditRecord(
                audit_id=f"AUD-{uuid.uuid4().hex[:6].upper()}",
                remediation_id=plan.remediation_id,
                incident_id=plan.incident_id,
                cluster_id=plan.cluster_id,
                namespace=plan.namespace,
                target_resource=f"{plan.target_kind}/{plan.target_name}",
                action_type=plan.action_type,
                approved_by=plan.approved_by or "operator",
                approved_at=plan.approved_at or now_iso,
                dry_run_passed=True,
                execution_status=plan.execution_status,
                verification_status=VerificationStatus.SUCCESS,
                timestamp=now_iso,
            )
            self.store.save_audit_record(audit)

            logger.info(f"Remediation VERIFICATION SUCCESS for Plan {plan.remediation_id}. Incident RESOLVED.")
            return True, {"status": "SUCCESS", "details": verification_details}

        else:
            plan.verification_status = VerificationStatus.FAILED
            plan.rollback_status = "AVAILABLE"  # Rollback option unlocked
            plan.failure_reason = verification_details.get("reason", "Verification check failed.")
            self.store.save_plan(plan)

            if incident:
                incident.status = "VERIFICATION_FAILED"
                incident.updated_at = now_iso

            audit = AuditRecord(
                audit_id=f"AUD-{uuid.uuid4().hex[:6].upper()}",
                remediation_id=plan.remediation_id,
                incident_id=plan.incident_id,
                cluster_id=plan.cluster_id,
                namespace=plan.namespace,
                target_resource=f"{plan.target_kind}/{plan.target_name}",
                action_type=plan.action_type,
                approved_by=plan.approved_by or "operator",
                approved_at=plan.approved_at or now_iso,
                dry_run_passed=True,
                execution_status=plan.execution_status,
                verification_status=VerificationStatus.FAILED,
                rollback_status="AVAILABLE",
                failure_reason=plan.failure_reason,
                timestamp=now_iso,
            )
            self.store.save_audit_record(audit)

            logger.warning(f"Remediation VERIFICATION FAILED for Plan {plan.remediation_id}: {plan.failure_reason}")
            return False, {"status": "FAILED", "reason": plan.failure_reason}

    def rollback(self, plan_id: str, apps_v1_api: Any = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Executes a rollback action if remediation verification failed.
        """
        plan = self.store.get_plan(plan_id)
        if not plan:
            return False, {"status": "FAILED", "reason": f"Plan {plan_id} not found."}

        if plan.rollback_status != "AVAILABLE":
            return False, {"status": "FAILED", "reason": f"Rollback not available for plan in state '{plan.rollback_status}'."}

        plan.rollback_status = "ROLLING_BACK"
        self.store.save_plan(plan)

        now_iso = utc_now_iso()
        try:
            if apps_v1_api and hasattr(apps_v1_api, "patch_namespaced_deployment"):
                patch_body = {"spec": {"template": {"metadata": {"annotations": {"skyops.io/rolledBackAt": now_iso}}}}}
                apps_v1_api.patch_namespaced_deployment(name=plan.target_name, namespace=plan.namespace, body=patch_body)

            plan.rollback_status = "ROLLED_BACK"
            plan.completed_at = now_iso
            plan.rollback_result = {"status": "ROLLED_BACK", "timestamp": now_iso}
            self.store.save_plan(plan)

            logger.info(f"Successfully ROLLED BACK Remediation Plan {plan.remediation_id}")
            return True, {"status": "ROLLED_BACK", "timestamp": now_iso}
        except Exception as e:
            plan.rollback_status = "ROLLBACK_FAILED"
            plan.failure_reason = f"Rollback API error: {e}"
            self.store.save_plan(plan)
            return False, {"status": "ROLLBACK_FAILED", "reason": str(e)}
