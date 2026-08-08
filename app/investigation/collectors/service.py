import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("SkyOps.ServiceCollector")


class ServiceCollector:
    """
    Discovers ALL Kubernetes Services targeting an affected Pod by matching
    Service selectors against Pod labels.
    """

    @staticmethod
    def collect(
        v1_api: Any,
        namespace: str,
        pod_name: str,
        pod_labels: Dict[str, str]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]], List[Dict[str, Any]]]:
        """
        Returns: (services, relationships, findings)
        """
        services = []
        relationships = []
        findings = []

        if not v1_api or not pod_labels:
            return services, relationships, findings

        try:
            svc_list = v1_api.list_namespaced_service(namespace=namespace)
            for item in svc_list.items:
                meta = getattr(item, "metadata", None)
                spec = getattr(item, "spec", None)
                if not meta or not spec:
                    continue

                selector = getattr(spec, "selector", None) or {}
                if not selector:
                    continue

                # Check if selector matches pod_labels
                is_match = True
                for k, v in selector.items():
                    if pod_labels.get(k) != v:
                        is_match = False
                        break

                if is_match:
                    svc_name = getattr(meta, "name", "")
                    svc_type = getattr(spec, "type", "ClusterIP")
                    cluster_ip = getattr(spec, "cluster_ip", "")
                    external_ips = getattr(spec, "external_i_ps", []) or getattr(spec, "external_ips", []) or []

                    ports = []
                    if hasattr(spec, "ports") and spec.ports:
                        for p in spec.ports:
                            ports.append({
                                "name": getattr(p, "name", ""),
                                "port": getattr(p, "port", 0),
                                "protocol": getattr(p, "protocol", "TCP"),
                                "target_port": str(getattr(p, "target_port", "")),
                                "node_port": getattr(p, "node_port", None),
                            })

                    svc_info = {
                        "name": svc_name,
                        "namespace": namespace,
                        "uid": getattr(meta, "uid", ""),
                        "type": svc_type,
                        "cluster_ip": cluster_ip,
                        "external_ips": external_ips,
                        "selector": selector,
                        "ports": ports,
                        "session_affinity": getattr(spec, "session_affinity", "None"),
                        "creation_timestamp": str(getattr(meta, "creation_timestamp", "")),
                    }
                    services.append(svc_info)

                    # Relationship: Service SELECTS Pod
                    relationships.append({
                        "from": f"Service/{namespace}/{svc_name}",
                        "relationship": "SELECTS",
                        "to": f"Pod/{namespace}/{pod_name}"
                    })

        except Exception as e:
            logger.warning(f"Failed to list services in namespace {namespace}: {e}")
            findings.append({
                "severity": "WARNING",
                "category": "SERVICE",
                "message": f"Could not list services in namespace {namespace}: {e}",
                "evidence": [str(e)]
            })

        return services, relationships, findings
