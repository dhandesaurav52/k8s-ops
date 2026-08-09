import logging
import re
from typing import Any, Dict, List, Tuple

from app.remediation.models import ActionType

logger = logging.getLogger("SkyOps.ActionCatalog")

ALLOWED_ACTION_TYPES = {
    ActionType.ROLLOUT_RESTART: {
        "risk_level": "LOW",
        "description": "Safe rollout restart of Deployment, StatefulSet, or DaemonSet",
        "supported_kinds": ["Deployment", "StatefulSet", "DaemonSet", "Pod"],
    },
    ActionType.SCALE_WORKLOAD: {
        "risk_level": "MEDIUM",
        "description": "Adjust replica count of Deployment or StatefulSet within configured policy bounds",
        "supported_kinds": ["Deployment", "StatefulSet"],
    },
    ActionType.ROLLBACK_WORKLOAD: {
        "risk_level": "MEDIUM",
        "description": "Rollback Deployment or StatefulSet to previous revision",
        "supported_kinds": ["Deployment", "StatefulSet"],
    },
    ActionType.RESOURCE_ADJUSTMENT: {
        "risk_level": "MEDIUM",
        "description": "Update memory or CPU limits/requests on workload container",
        "supported_kinds": ["Deployment", "StatefulSet", "DaemonSet"],
    },
}

FORBIDDEN_KEYWORDS = [
    "DELETE NAMESPACE",
    "DELETE PV",
    "DELETE PVC",
    "DELETE SECRET",
    "DELETE DATABASE",
    "RM -RF",
    "EXEC",
    "SUBPROCESS",
    "SH ",
    "BASH ",
    "SUDO ",
    "CLUSTER-ADMIN",
    "DROP TABLE",
    "DROP DATABASE",
    "KUBECTL EXEC",
]


class SafeActionCatalog:
    """
    Safe Action Catalog & Allowlist Validator.
    Strictly enforces allowlisted Kubernetes actions and blocks arbitrary shell code execution.
    """

    @staticmethod
    def is_action_allowlisted(
        action_type: str,
        command_str: str = "",
        target_kind: str = "Deployment",
    ) -> Tuple[bool, str, str]:
        """
        Validates whether an action is safe and allowlisted.
        Returns: (is_allowlisted, risk_level, reason)
        """
        # Check forbidden keywords in command string
        upper_cmd = command_str.upper()
        for kw in FORBIDDEN_KEYWORDS:
            if kw in upper_cmd:
                logger.warning(f"Forbidden keyword '{kw}' detected in remediation command proposal: {command_str}")
                return False, "HIGH", f"Forbidden command pattern detected ('{kw}'). Action requires manual intervention."

        if action_type not in ALLOWED_ACTION_TYPES:
            return False, "HIGH", f"Action type '{action_type}' is not allowlisted. Action requires manual intervention."

        catalog_entry = ALLOWED_ACTION_TYPES[action_type]
        supported_kinds = catalog_entry["supported_kinds"]

        if target_kind and target_kind not in supported_kinds:
            # If target is Pod, map to Deployment if possible, or allow rollout restart if pod belongs to deployment
            if target_kind == "Pod" and action_type in [ActionType.ROLLOUT_RESTART, ActionType.SCALE_WORKLOAD, ActionType.RESOURCE_ADJUSTMENT]:
                pass  # Supported via workload controller parent resolution
            else:
                return (
                    False,
                    "HIGH",
                    f"Resource kind '{target_kind}' is not supported for action '{action_type}'. Supported kinds: {supported_kinds}",
                )

        return True, catalog_entry["risk_level"], catalog_entry["description"]

    @staticmethod
    def map_recommendation_to_proposal(
        incident_id: str,
        cluster_id: str,
        resource_kind: str,
        resource_name: str,
        namespace: str,
        recommendation: str = "",
        mitigation_cmd: str = "",
        category: str = "",
        target_uid: str = "",
    ) -> Dict[str, Any]:
        """
        Converts AI / Diagnosis recommendation text into a structured, allowlisted remediation proposal.
        Strictly prevents arbitrary command injection.
        """
        cmd_text = f"{recommendation} {mitigation_cmd}".lower()

        # Derive target workload kind & name (e.g. payment-processor pod -> Deployment/payment-processor)
        target_kind = resource_kind
        target_name = resource_name
        if target_kind == "Pod" and "-" in resource_name:
            # Common k8s naming: deployment-hash-podid or deployment-sts-index
            parts = resource_name.split("-")
            if len(parts) >= 3:
                target_name = "-".join(parts[:-2])
                target_kind = "Deployment"
            elif len(parts) == 2 and parts[-1].isdigit():
                target_name = parts[0]
                target_kind = "StatefulSet"
            else:
                target_name = parts[0]
                target_kind = "Deployment"

        action_type = ActionType.UNSUPPORTED
        action_params: Dict[str, Any] = {}
        command_action = ""
        reason = f"Remediation proposed for {category} incident on {namespace}/{resource_name}"

        # 1. Rollout restart
        if "restart" in cmd_text or "rollout restart" in cmd_text or "crashloop" in category.lower():
            action_type = ActionType.ROLLOUT_RESTART
            command_action = f"kubectl rollout restart {target_kind.lower()}/{target_name} -n {namespace}"
            action_params = {"workload_kind": target_kind, "workload_name": target_name}

        # 2. Rollback
        elif "rollback" in cmd_text or "undo" in cmd_text or "imagepull" in category.lower():
            action_type = ActionType.ROLLBACK_WORKLOAD
            command_action = f"kubectl rollout undo {target_kind.lower()}/{target_name} -n {namespace}"
            action_params = {"workload_kind": target_kind, "workload_name": target_name, "to_revision": 0}

        # 3. Resource adjustment (e.g., OOMKilled)
        elif "oom" in category.lower() or "memory limit" in cmd_text or "increase memory" in cmd_text or "patch" in cmd_text:
            action_type = ActionType.RESOURCE_ADJUSTMENT
            command_action = f"kubectl set resources {target_kind.lower()}/{target_name} -n {namespace} --limits=memory=1Gi,cpu=500m"
            action_params = {
                "workload_kind": target_kind,
                "workload_name": target_name,
                "memory_limit": "1Gi",
                "cpu_limit": "500m",
            }

        # 4. Scale workload
        elif "scale" in cmd_text or "replicas" in cmd_text:
            action_type = ActionType.SCALE_WORKLOAD
            replicas = 2
            match = re.search(r"replicas[=\s]+(\d+)", cmd_text)
            if match:
                replicas = int(match.group(1))
            command_action = f"kubectl scale {target_kind.lower()}/{target_name} -n {namespace} --replicas={replicas}"
            action_params = {"workload_kind": target_kind, "workload_name": target_name, "replicas": replicas}

        # Validate against catalog
        is_allowed, risk, check_reason = SafeActionCatalog.is_action_allowlisted(action_type, command_action, target_kind)

        if not is_allowed:
            action_type = ActionType.UNSUPPORTED
            command_action = "Action requires manual intervention."

        return {
            "incident_id": incident_id,
            "cluster_id": cluster_id,
            "target_kind": target_kind,
            "target_name": target_name,
            "namespace": namespace,
            "target_uid": target_uid,
            "action_type": action_type,
            "command_action": command_action,
            "action_params": action_params,
            "reason": reason,
            "risk_level": risk,
        }
