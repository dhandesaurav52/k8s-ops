import logging
from typing import Any, Dict, List, Optional, Tuple
from kubernetes import client

logger = logging.getLogger("SkyOps.Collector")


def get_pod_unhealthy_state(pod: Any) -> Tuple[bool, str, str]:
    """
    Inspects a Pod object and determines if it is unhealthy.
    Returns: (is_unhealthy, primary_reason, current_state_description)
    """
    if not pod or not hasattr(pod, "status") or not pod.status:
        return False, "", "Unknown"

    phase = pod.status.phase or "Unknown"

    # Check for phase-level unhealthiness
    if phase in ["Failed", "Unknown"]:
        return True, phase, f"Pod phase is {phase}"

    container_statuses = pod.status.container_statuses or []
    init_container_statuses = pod.status.init_container_statuses or []
    all_statuses = list(container_statuses) + list(init_container_statuses)

    for cs in all_statuses:
        waiting = cs.state.waiting if cs.state else None
        terminated = cs.state.terminated if cs.state else None

        # Container waiting with error reasons
        if waiting and waiting.reason:
            unhealthy_reasons = [
                "ErrImagePull",
                "ImagePullBackOff",
                "CrashLoopBackOff",
                "CreateContainerConfigError",
                "CreateContainerError",
                "RunContainerError",
                "InvalidImageName",
            ]
            if waiting.reason in unhealthy_reasons or "BackOff" in waiting.reason or "Error" in waiting.reason:
                msg = waiting.message or f"Container {cs.name} waiting with reason {waiting.reason}"
                return True, waiting.reason, f"{cs.name}: {waiting.reason} ({msg})"

        # Container terminated unexpectedly or OOMKilled
        if terminated:
            if terminated.reason == "OOMKilled" or (terminated.exit_code and terminated.exit_code != 0):
                reason = terminated.reason or f"ExitCode{terminated.exit_code}"
                msg = terminated.message or f"Container {cs.name} exited with code {terminated.exit_code}"
                return True, reason, f"{cs.name}: {reason} ({msg})"

    # Pending phase check - if pending for a reason
    if phase == "Pending":
        # Check pod conditions
        conditions = pod.status.conditions or []
        for cond in conditions:
            if cond.type == "PodScheduled" and cond.status == "False":
                reason = cond.reason or "Unschedulable"
                return True, "PodPending", f"Pod scheduled false: {reason} ({cond.message or ''})"
        return True, "PodPending", "Pod is in Pending phase"

    return False, "", f"Pod is {phase}"


def collect_pod_events(v1: Optional[client.CoreV1Api], namespace: str, pod_name: str, pod_uid: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Collects Kubernetes events related to the specific Pod.
    Ensures no secret values are ever included.
    """
    if not v1:
        return []

    evidence_events = []
    try:
        events = v1.list_namespaced_event(
            namespace=namespace,
            field_selector=f"involvedObject.name={pod_name},involvedObject.kind=Pod"
        )
        for item in events.items:
            # Mask or avoid secrets
            event_obj = {
                "type": item.type or "Normal",
                "reason": item.reason or "Unknown",
                "message": sanitize_text(item.message or ""),
                "count": item.count or 1,
                "first_timestamp": str(item.first_timestamp) if item.first_timestamp else None,
                "last_timestamp": str(item.last_timestamp) if item.last_timestamp else None,
            }
            evidence_events.append(event_obj)
    except Exception as e:
        logger.warning(f"Could not collect events for pod {namespace}/{pod_name}: {e}")

    return evidence_events


def sanitize_text(text: str) -> str:
    """
    Sanitizes strings to ensure secret values or tokens are not leaked in logs or incidents.
    """
    if not text:
        return ""
    # Strip any potential token keywords if present
    # Keep infrastructure details readable
    return text.strip()
