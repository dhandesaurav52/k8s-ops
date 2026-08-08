import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("SkyOps.DiagnosisEngine")


class DiagnosisEngine:
    """
    Deterministic Diagnosis Engine.
    Analyzes Kubernetes state, container failure reasons, exit codes, and event messages
    to provide root cause, severity, evidence summary, and recommended actions.
    """

    @staticmethod
    def diagnose(category: str, current_state: str, events: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Runs deterministic rule checks based on failure category, current state, and collected events.
        Returns: (diagnosis_dict, recommendations_list)
        """
        category_upper = category.upper()
        state_upper = current_state.upper()

        # Gather event texts for searching keywords
        event_texts = [e.get("message", "") for e in events]
        full_event_log = " ".join(event_texts)

        # 1. Image Pull Failures
        if "IMAGE" in category_upper or "ERRIMAGEPULL" in state_upper or "IMAGEPULLBACKOFF" in state_upper:
            severity = "MEDIUM"
            if "NOTFOUND" in full_event_log.upper() or "404" in full_event_log:
                root_cause = "Container image non-existent or image tag not found in target registry."
            elif "DENIED" in full_event_log.upper() or "UNAUTHORIZED" in full_event_log.upper():
                root_cause = "Authentication failed when attempting to pull container image (Missing or invalid imagePullSecrets)."
            else:
                root_cause = "Image pull failure due to network timeout or inaccessible container registry."

            recommendations = [
                "Verify the container image repository path and tag spelling in Pod spec.",
                "Ensure image exists in registry or pull secret is configured in pod/namespace.",
                "Check cluster egress network rules or registry accessibility.",
            ]
            diagnosis = {
                "incident_category": "ImagePullFailure",
                "severity": severity,
                "root_cause": root_cause,
                "evidence": f"State: {current_state} | Events: {len(events)} events collected",
            }
            return diagnosis, recommendations

        # 2. CrashLoopBackOff / Process Exit Errors
        if "CRASH" in category_upper or "CRASHLOOPBACKOFF" in state_upper or "EXITCODE" in state_upper:
            severity = "HIGH"
            root_cause = "Application container started but exited prematurely with an error code."
            if "EXITCODE137" in state_upper or "OOM" in full_event_log.upper():
                severity = "CRITICAL"
                root_cause = "Container terminated due to Out-Of-Memory (OOM) or SIGKILL signal."

            recommendations = [
                "Inspect container stdout/stderr logs via `kubectl logs`.",
                "Check application startup commands, environment variables, and config files.",
                "Verify container resource limits (CPU/Memory).",
            ]
            diagnosis = {
                "incident_category": "CrashLoopBackOff",
                "severity": severity,
                "root_cause": root_cause,
                "evidence": f"State: {current_state}",
            }
            return diagnosis, recommendations

        # 3. OOMKilled
        if "OOM" in category_upper or "OOMKILLED" in state_upper:
            severity = "CRITICAL"
            root_cause = "Container exceeded memory allocation limit and was killed by Linux OOM killer."
            recommendations = [
                "Increase container memory limit in pod definition.",
                "Check application for memory leaks or excessive heap consumption.",
            ]
            diagnosis = {
                "incident_category": "OOMKilled",
                "severity": severity,
                "root_cause": root_cause,
                "evidence": f"State: {current_state}",
            }
            return diagnosis, recommendations

        # 4. Config & Secret Errors
        if "CONFIG" in category_upper or "CREATECONTAINERCONFIGERROR" in state_upper:
            severity = "HIGH"
            root_cause = "Pod configuration failure (e.g., missing ConfigMap, Secret, or key reference)."
            recommendations = [
                "Verify referenced ConfigMaps and Secrets exist in the namespace.",
                "Check key names inside referenced ConfigMap/Secret against Pod env/volume spec.",
            ]
            diagnosis = {
                "incident_category": "ContainerConfigError",
                "severity": severity,
                "root_cause": root_cause,
                "evidence": f"State: {current_state}",
            }
            return diagnosis, recommendations

        # 5. Pod Pending / Unschedulable
        if "PENDING" in category_upper or "PENDING" in state_upper:
            severity = "MEDIUM"
            root_cause = "Pod cannot be scheduled onto any cluster node due to resource constraints or taints."
            recommendations = [
                "Check cluster node CPU/Memory capacity.",
                "Inspect node selectors, taints, tolerations, and affinity rules.",
                "Verify PVC bound status if persistent volumes are attached.",
            ]
            diagnosis = {
                "incident_category": "PodPending",
                "severity": severity,
                "root_cause": root_cause,
                "evidence": f"State: {current_state}",
            }
            return diagnosis, recommendations

        # Generic / Fallback
        diagnosis = {
            "incident_category": category,
            "severity": "MEDIUM",
            "root_cause": f"Unhealthy workload detected with state: {current_state}.",
            "evidence": f"State: {current_state}",
        }
        recommendations = [
            "Inspect pod status and events using `kubectl describe pod`.",
            "Review application logs.",
        ]
        return diagnosis, recommendations
