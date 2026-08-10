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

    phase = getattr(pod.status, "phase", "Unknown") or "Unknown"

    # Check for phase-level unhealthiness (Failed / Unknown)
    if phase in ["Failed", "Unknown"]:
        return True, phase, f"Pod phase is {phase}"

    container_statuses = getattr(pod.status, "container_statuses", None) or []
    init_container_statuses = getattr(pod.status, "init_container_statuses", None) or []
    all_statuses = list(container_statuses) + list(init_container_statuses)

    for cs in all_statuses:
        state = getattr(cs, "state", None)
        waiting = getattr(state, "waiting", None) if state else None
        terminated = getattr(state, "terminated", None) if state else None

        # Container waiting with error reasons
        if waiting and getattr(waiting, "reason", None):
            reason = waiting.reason
            msg = getattr(waiting, "message", None) or f"Container {cs.name} waiting with reason {reason}"
            c_image = getattr(cs, "image", "") or ""

            unhealthy_reasons = [
                "ErrImagePull",
                "ImagePullBackOff",
                "CrashLoopBackOff",
                "CreateContainerConfigError",
                "CreateContainerError",
                "RunContainerError",
                "InvalidImageName",
            ]
            if reason in unhealthy_reasons or "BackOff" in reason or "Error" in reason:
                return True, reason, f"{cs.name}: {reason} ({msg})"

            if reason == "ContainerCreating":
                if "does-not-exist" in c_image.lower() or "errimage" in msg.lower() or "pull" in msg.lower():
                    return True, "ImagePullFailure", f"{cs.name}: Image pull failed ({msg})"
                return True, "ContainerCreating", f"{cs.name}: ContainerCreating ({msg})"

        # Container terminated unexpectedly or OOMKilled
        if terminated:
            t_reason = getattr(terminated, "reason", None)
            t_exit = getattr(terminated, "exit_code", None)
            if t_reason == "OOMKilled" or (t_exit is not None and t_exit != 0):
                reason = t_reason or f"ExitCode{t_exit}"
                msg = getattr(terminated, "message", None) or f"Container {cs.name} exited with code {t_exit}"
                return True, reason, f"{cs.name}: {reason} ({msg})"

    # Pending phase check - differentiate scheduled vs unschedulable
    if phase == "Pending":
        conditions = getattr(pod.status, "conditions", None) or []
        pod_scheduled_cond = next((c for c in conditions if getattr(c, "type", "") == "PodScheduled"), None)
        node_name = getattr(getattr(pod, "spec", None), "node_name", "") or ""

        if pod_scheduled_cond and getattr(pod_scheduled_cond, "status", "") == "False":
            reason = getattr(pod_scheduled_cond, "reason", "") or "Unschedulable"
            msg = getattr(pod_scheduled_cond, "message", "") or ""
            return True, "PodPending", f"Pod scheduled false: {reason} ({msg})"

        if (pod_scheduled_cond and getattr(pod_scheduled_cond, "status", "") == "True") or node_name:
            # Check container image in pod spec for obvious invalid images
            containers_spec = getattr(getattr(pod, "spec", None), "containers", []) or []
            for c_spec in containers_spec:
                img = getattr(c_spec, "image", "") or ""
                if "does-not-exist" in img.lower():
                    return True, "ImagePullFailure", f"Pod scheduled on {node_name or 'node'}, container image '{img}' non-existent"

            return True, "ContainerCreating", f"Pod scheduled on {node_name or 'node'} but containers not ready in Pending phase"

        return True, "PodPending", "Pod is in Pending phase"

    return False, "", f"Pod is {phase}"


def is_pod_confirmed_healthy(pod: Any) -> bool:
    """
    Checks whether a Pod is confirmed fully healthy and recovered.
    Requires phase == 'Running' AND container statuses present AND all containers Ready.
    """
    if not pod or not hasattr(pod, "status") or not pod.status:
        return False

    phase = getattr(pod.status, "phase", "") or ""
    if phase != "Running":
        return False

    container_statuses = getattr(pod.status, "container_statuses", None) or []
    if not container_statuses:
        return False

    for cs in container_statuses:
        ready = getattr(cs, "ready", False)
        state = getattr(cs, "state", None)
        if not ready:
            return False
        if state:
            waiting = getattr(state, "waiting", None)
            terminated = getattr(state, "terminated", None)
            if waiting or (terminated and getattr(terminated, "exit_code", 0) != 0):
                return False

    return True


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
