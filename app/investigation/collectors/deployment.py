import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("SkyOps.DeploymentCollector")


class DeploymentCollector:
    """
    Collects state, rollout status, and findings for a Deployment.
    """

    @staticmethod
    def collect(
        apps_v1_api: Any,
        namespace: str,
        dep_name: str
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Returns: (deployment_info, findings)
        """
        if not apps_v1_api or not dep_name:
            return {}, []

        try:
            dep = apps_v1_api.read_namespaced_deployment(name=dep_name, namespace=namespace)
        except Exception as e:
            logger.warning(f"Failed to fetch Deployment {namespace}/{dep_name}: {e}")
            return {}, [{
                "severity": "WARNING",
                "category": "DEPLOYMENT",
                "message": f"Could not retrieve Deployment {namespace}/{dep_name}: {e}",
                "evidence": [str(e)]
            }]

        meta = getattr(dep, "metadata", None)
        spec = getattr(dep, "spec", None)
        status = getattr(dep, "status", None)

        desired = getattr(spec, "replicas", 0) if spec else 0
        replicas = getattr(status, "replicas", 0) or 0 if status else 0
        updated = getattr(status, "updated_replicas", 0) or 0 if status else 0
        ready = getattr(status, "ready_replicas", 0) or 0 if status else 0
        available = getattr(status, "available_replicas", 0) or 0 if status else 0
        unavailable = getattr(status, "unavailable_replicas", 0) or 0 if status else 0

        generation = getattr(meta, "generation", None) if meta else None
        observed_generation = getattr(status, "observed_generation", None) if status else None

        conditions = []
        if status and hasattr(status, "conditions") and status.conditions:
            for c in status.conditions:
                conditions.append({
                    "type": getattr(c, "type", ""),
                    "status": getattr(c, "status", ""),
                    "reason": getattr(c, "reason", ""),
                    "message": getattr(c, "message", ""),
                    "last_transition_time": str(getattr(c, "last_transition_time", "")),
                })

        dep_info = {
            "name": getattr(meta, "name", dep_name) if meta else dep_name,
            "namespace": getattr(meta, "namespace", namespace) if meta else namespace,
            "uid": getattr(meta, "uid", "") if meta else "",
            "creation_timestamp": str(getattr(meta, "creation_timestamp", "")) if meta else "",
            "labels": getattr(meta, "labels", {}) or {} if meta else {},
            "generation": generation,
            "observed_generation": observed_generation,
            "desired_replicas": desired,
            "replicas": replicas,
            "updated_replicas": updated,
            "ready_replicas": ready,
            "available_replicas": available,
            "unavailable_replicas": unavailable,
            "conditions": conditions,
        }

        findings = []

        if generation is not None and observed_generation is not None and observed_generation < generation:
            findings.append({
                "severity": "WARNING",
                "category": "DEPLOYMENT",
                "message": f"Deployment '{dep_name}' generation ({generation}) has not been fully processed by controller (observed generation: {observed_generation})",
                "evidence": [f"generation: {generation}", f"observed_generation: {observed_generation}"]
            })

        if desired > 0 and ready < desired:
            findings.append({
                "severity": "WARNING",
                "category": "DEPLOYMENT",
                "message": f"Deployment '{dep_name}' has unready replicas: {ready}/{desired} ready ({unavailable} unavailable)",
                "evidence": [f"desired: {desired}", f"ready: {ready}", f"unavailable: {unavailable}"]
            })

        # Check conditions for Progressing / Available False
        for cond in conditions:
            if cond["type"] == "Progressing" and cond["status"] == "False":
                findings.append({
                    "severity": "CRITICAL",
                    "category": "DEPLOYMENT",
                    "message": f"Deployment '{dep_name}' rollout stalled: {cond.get('reason')} ({cond.get('message')})",
                    "evidence": [f"reason: {cond.get('reason')}", f"message: {cond.get('message')}"]
                })
            elif cond["type"] == "Available" and cond["status"] == "False":
                findings.append({
                    "severity": "CRITICAL",
                    "category": "DEPLOYMENT",
                    "message": f"Deployment '{dep_name}' is unavailable: {cond.get('reason')} ({cond.get('message')})",
                    "evidence": [f"reason: {cond.get('reason')}", f"message: {cond.get('message')}"]
                })

        return dep_info, findings
