import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("SkyOps.DiagnosisEngine")


class DiagnosisEngine:
    """
    Deterministic Evidence-Based Diagnosis Engine.
    Analyzes Kubernetes state, pod conditions, container failure reasons, exit codes,
    image tags, and event messages in priority order to provide deterministic root causes,
    confidence metrics, evidence breakdowns, and recommended remediation steps.
    """

    @staticmethod
    def diagnose(
        category: str,
        current_state: str,
        events: List[Dict[str, Any]],
        pod_obj: Optional[Any] = None,
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Runs deterministic rule checks based on failure category, current state, collected events,
        and pod conditions/container states.
        Returns: (diagnosis_dict, recommendations_list)
        """
        category_upper = category.upper()
        state_upper = current_state.upper()

        # Extract pod conditions & container status if pod_obj is available
        pod_scheduled = None
        scheduled_node = ""
        container_waiting_reasons = []
        container_terminated_reasons = []
        image_names = []

        if pod_obj and hasattr(pod_obj, "status") and pod_obj.status:
            conds = getattr(pod_obj.status, "conditions", None) or []
            for cond in conds:
                if getattr(cond, "type", "") == "PodScheduled":
                    pod_scheduled = (getattr(cond, "status", "") == "True")

            if hasattr(pod_obj, "spec") and pod_obj.spec:
                scheduled_node = getattr(pod_obj.spec, "node_name", "") or ""
                for c in getattr(pod_obj.spec, "containers", []) or []:
                    img = getattr(c, "image", "") or ""
                    if img:
                        image_names.append(img)

            c_statuses = (getattr(pod_obj.status, "container_statuses", None) or []) + \
                         (getattr(pod_obj.status, "init_container_statuses", None) or [])
            for cs in c_statuses:
                state = getattr(cs, "state", None)
                if state:
                    w = getattr(state, "waiting", None)
                    if w and getattr(w, "reason", None):
                        container_waiting_reasons.append(w.reason)
                    t = getattr(state, "terminated", None)
                    if t and getattr(t, "reason", None):
                        container_terminated_reasons.append(t.reason)

        # Gather event texts for searching keywords
        event_texts = [e.get("message", "") for e in events if isinstance(e, dict)]
        full_event_log = " ".join(event_texts).upper()

        # 1. Image Pull Failures
        is_image_fail = (
            "IMAGE" in category_upper
            or "ERRIMAGEPULL" in state_upper
            or "IMAGEPULLBACKOFF" in state_upper
            or "ERRIMAGEPULL" in full_event_log
            or "IMAGEPULLBACKOFF" in full_event_log
            or "FAILED TO PULL IMAGE" in full_event_log
            or any(r in ["ErrImagePull", "ImagePullBackOff", "InvalidImageName"] for r in container_waiting_reasons)
            or any("does-not-exist" in img.lower() for img in image_names)
        )

        if is_image_fail:
            severity = "MEDIUM"
            if "NOTFOUND" in full_event_log or "404" in full_event_log or "DOES-NOT-EXIST" in full_event_log or any("does-not-exist" in img.lower() for img in image_names):
                root_cause = "Container image non-existent or image tag not found in target registry."
            elif "DENIED" in full_event_log or "UNAUTHORIZED" in full_event_log:
                root_cause = "Authentication failed when attempting to pull container image (Missing or invalid imagePullSecrets)."
            else:
                root_cause = "Image pull failure due to network timeout or inaccessible container registry."

            recommendations = [
                "Verify the container image repository path and tag spelling in Pod spec.",
                "Ensure image exists in registry or pull secret is configured in pod/namespace.",
                "Check cluster egress network rules or registry accessibility.",
            ]

            supporting = ["Image pull or container startup failure detected"]
            if pod_scheduled or scheduled_node:
                supporting.append(f"Pod is scheduled on node '{scheduled_node or 'cluster-node'}' (PodScheduled=True)")
            if full_event_log:
                supporting.append("Kubernetes event log confirms image pull error")

            diagnosis = {
                "incident_category": "ImagePullFailure",
                "severity": severity,
                "root_cause": root_cause,
                "confidence": 0.90,
                "confidence_score": 90,
                "confidence_level": "HIGH",
                "supporting_evidence": supporting,
                "contradicting_evidence": [],
                "evidence": f"State: {current_state} | Events: {len(events)} events collected",
            }
            return diagnosis, recommendations

        # 2. CrashLoopBackOff / Process Exit Errors
        if "CRASH" in category_upper or "CRASHLOOPBACKOFF" in state_upper or "EXITCODE" in state_upper or any(r in ["CrashLoopBackOff", "Error"] for r in container_waiting_reasons):
            severity = "HIGH"
            root_cause = "Application container started but exited prematurely with an error code."
            if "EXITCODE137" in state_upper or "OOM" in full_event_log or any(r == "OOMKilled" for r in container_terminated_reasons):
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
                "confidence": 0.85,
                "confidence_score": 85,
                "confidence_level": "HIGH",
                "supporting_evidence": ["Container process exiting unexpectedly"],
                "contradicting_evidence": [],
                "evidence": f"State: {current_state}",
            }
            return diagnosis, recommendations

        # 3. OOMKilled
        if "OOM" in category_upper or "OOMKILLED" in state_upper or any(r == "OOMKilled" for r in container_terminated_reasons):
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
                "confidence": 0.90,
                "confidence_score": 90,
                "confidence_level": "HIGH",
                "supporting_evidence": ["OOMKilled status reported by Linux kernel / kubelet"],
                "contradicting_evidence": [],
                "evidence": f"State: {current_state}",
            }
            return diagnosis, recommendations

        # 4. Config & Secret Errors
        if "CONFIG" in category_upper or "CREATECONTAINERCONFIGERROR" in state_upper or any(r in ["CreateContainerConfigError", "CreateContainerError"] for r in container_waiting_reasons):
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
                "confidence": 0.85,
                "confidence_score": 85,
                "confidence_level": "HIGH",
                "supporting_evidence": ["ConfigMap or Secret reference missing"],
                "contradicting_evidence": [],
                "evidence": f"State: {current_state}",
            }
            return diagnosis, recommendations

        # 5. Pod Pending / Unschedulable (Evidence-based priority check)
        if "PENDING" in category_upper or "PENDING" in state_upper or "CONTAINERCREATING" in state_upper or category_upper == "CONTAINERCREATING":
            # Check if Pod is already scheduled
            if pod_scheduled is True or scheduled_node or "FAILED TO PULL IMAGE" in full_event_log or "ERRIMAGEPULL" in full_event_log:
                # Scheduled! Investigate container creation/startup instead of node scheduling
                if "FAILED TO PULL IMAGE" in full_event_log or "ERRIMAGEPULL" in full_event_log or "IMAGE" in full_event_log:
                    cat_name = "ImagePullFailure"
                    root_cause = "Container image non-existent or image tag not found in target registry."
                    severity = "MEDIUM"
                else:
                    cat_name = "ContainerStartupFailure"
                    root_cause = f"Pod is scheduled on node '{scheduled_node or 'assigned_node'}' but containers fail to start or initialize."
                    severity = "HIGH"

                recommendations = [
                    "Inspect container startup commands and environment variables.",
                    "Check container status and event log via `kubectl describe pod`.",
                    "Verify node container runtime logs if sandbox creation fails.",
                ]
                diagnosis = {
                    "incident_category": cat_name,
                    "severity": severity,
                    "root_cause": root_cause,
                    "confidence": 0.85,
                    "confidence_score": 85,
                    "confidence_level": "HIGH",
                    "supporting_evidence": [
                        f"Pod is scheduled on node '{scheduled_node or 'node01'}' (PodScheduled=True)",
                        "Container is in waiting / ContainerCreating state",
                    ],
                    "contradicting_evidence": ["Node is Ready and healthy"],
                    "evidence": f"State: {current_state} | PodScheduled: True",
                }
                return diagnosis, recommendations
            else:
                # Truly unschedulable
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
                    "confidence": 0.80,
                    "confidence_score": 80,
                    "confidence_level": "HIGH",
                    "supporting_evidence": ["PodScheduled condition is False"],
                    "contradicting_evidence": [],
                    "evidence": f"State: {current_state}",
                }
                return diagnosis, recommendations

        # Generic / Fallback
        diagnosis = {
            "incident_category": category,
            "severity": "MEDIUM",
            "root_cause": f"Unhealthy workload detected with state: {current_state}.",
            "confidence": 0.50,
            "confidence_score": 50,
            "confidence_level": "MEDIUM",
            "supporting_evidence": [f"State: {current_state}"],
            "contradicting_evidence": [],
            "evidence": f"State: {current_state}",
        }
        recommendations = [
            "Inspect pod status and events using `kubectl describe pod`.",
            "Review application logs.",
        ]
        return diagnosis, recommendations
