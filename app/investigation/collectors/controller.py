import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("SkyOps.ControllerCollector")


class ControllerCollector:
    """
    Traces the controller ownership chain starting from a Pod's ownerReferences
    (e.g., Pod -> ReplicaSet -> Deployment).
    """

    @staticmethod
    def collect(
        apps_v1_api: Any,
        namespace: str,
        owner_references: List[Dict[str, Any]],
        pod_name: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]], List[Dict[str, Any]]]:
        """
        Returns: (controllers, relationships, findings)
        """
        controllers = []
        relationships = []
        findings = []

        if not owner_references:
            return controllers, relationships, findings

        current_child_kind = "Pod"
        current_child_name = pod_name

        owners_to_process = list(owner_references)

        while owners_to_process:
            owner = owners_to_process.pop(0)
            kind = owner.get("kind", "")
            name = owner.get("name", "")
            uid = owner.get("uid", "")

            if not kind or not name:
                continue

            # Record relationship
            rel = {
                "from": f"{current_child_kind}/{namespace}/{current_child_name}",
                "relationship": "OWNED_BY",
                "to": f"{kind}/{namespace}/{name}"
            }
            relationships.append(rel)

            ctrl_summary = {
                "kind": kind,
                "name": name,
                "namespace": namespace,
                "uid": uid,
            }
            controllers.append(ctrl_summary)

            # If controller is ReplicaSet, try to discover its parent (e.g. Deployment)
            if kind == "ReplicaSet" and apps_v1_api:
                try:
                    rs = apps_v1_api.read_namespaced_replica_set(name=name, namespace=namespace)
                    rs_meta = getattr(rs, "metadata", None)
                    if rs_meta and hasattr(rs_meta, "owner_references") and rs_meta.owner_references:
                        for rs_owner in rs_meta.owner_references:
                            owners_to_process.append({
                                "kind": getattr(rs_owner, "kind", ""),
                                "name": getattr(rs_owner, "name", ""),
                                "uid": getattr(rs_owner, "uid", ""),
                            })
                            current_child_kind = "ReplicaSet"
                            current_child_name = name
                except Exception as e:
                    logger.debug(f"Could not read owner references for ReplicaSet {namespace}/{name}: {e}")

        return controllers, relationships, findings
