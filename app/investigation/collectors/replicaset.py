import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("SkyOps.ReplicaSetCollector")


class ReplicaSetCollector:
    """
    Collects state and findings for a ReplicaSet.
    """

    @staticmethod
    def collect(
        apps_v1_api: Any,
        namespace: str,
        rs_name: str
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Returns: (replicaset_info, findings)
        """
        if not apps_v1_api or not rs_name:
            return {}, []

        try:
            rs = apps_v1_api.read_namespaced_replica_set(name=rs_name, namespace=namespace)
        except Exception as e:
            logger.warning(f"Failed to fetch ReplicaSet {namespace}/{rs_name}: {e}")
            return {}, [{
                "severity": "WARNING",
                "category": "REPLICASET",
                "message": f"Could not retrieve ReplicaSet {namespace}/{rs_name}: {e}",
                "evidence": [str(e)]
            }]

        meta = getattr(rs, "metadata", None)
        spec = getattr(rs, "spec", None)
        status = getattr(rs, "status", None)

        desired = getattr(spec, "replicas", 0) if spec else 0
        current = getattr(status, "replicas", 0) if status else 0
        ready = getattr(status, "ready_replicas", 0) or 0 if status else 0
        available = getattr(status, "available_replicas", 0) or 0 if status else 0
        fully_labeled = getattr(status, "fully_labeled_replicas", 0) or 0 if status else 0

        rs_info = {
            "name": getattr(meta, "name", rs_name) if meta else rs_name,
            "namespace": getattr(meta, "namespace", namespace) if meta else namespace,
            "uid": getattr(meta, "uid", "") if meta else "",
            "creation_timestamp": str(getattr(meta, "creation_timestamp", "")) if meta else "",
            "labels": getattr(meta, "labels", {}) or {} if meta else {},
            "desired_replicas": desired,
            "current_replicas": current,
            "ready_replicas": ready,
            "available_replicas": available,
            "fully_labeled_replicas": fully_labeled,
            "owner_references": [
                {
                    "kind": getattr(o, "kind", ""),
                    "name": getattr(o, "name", ""),
                    "uid": getattr(o, "uid", ""),
                } for o in (getattr(meta, "owner_references", []) or [])
            ] if meta else [],
        }

        findings = []
        if desired > 0 and ready < desired:
            findings.append({
                "severity": "WARNING",
                "category": "REPLICASET",
                "message": f"ReplicaSet '{rs_name}' has unready replicas: {ready}/{desired} ready",
                "evidence": [f"desired: {desired}", f"ready: {ready}", f"current: {current}"]
            })

        return rs_info, findings
