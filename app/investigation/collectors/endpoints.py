import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("SkyOps.EndpointsCollector")


class EndpointsCollector:
    """
    Collects Endpoint details and ready/unready status for Services targeting the Pod.
    """

    @staticmethod
    def collect(
        v1_api: Any,
        namespace: str,
        services: List[Dict[str, Any]],
        pod_ip: str = ""
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Returns: (endpoints_info_list, findings)
        """
        endpoints_list = []
        findings = []

        if not v1_api or not services:
            return endpoints_list, findings

        for svc in services:
            svc_name = svc.get("name")
            if not svc_name:
                continue

            try:
                ep = v1_api.read_namespaced_endpoints(name=svc_name, namespace=namespace)
                meta = getattr(ep, "metadata", None)
                subsets = getattr(ep, "subsets", None) or []

                ready_addresses = []
                not_ready_addresses = []
                ports = []

                for sub in subsets:
                    # Addresses
                    for addr in (getattr(sub, "addresses", []) or []):
                        ip = getattr(addr, "ip", "")
                        node_name = getattr(addr, "node_name", "")
                        target_ref = None
                        ref = getattr(addr, "target_ref", None)
                        if ref:
                            target_ref = {
                                "kind": getattr(ref, "kind", ""),
                                "name": getattr(ref, "name", ""),
                                "namespace": getattr(ref, "namespace", ""),
                            }
                        ready_addresses.append({
                            "ip": ip,
                            "node_name": node_name,
                            "target_ref": target_ref
                        })

                    # Not Ready Addresses
                    for addr in (getattr(sub, "not_ready_addresses", []) or []):
                        ip = getattr(addr, "ip", "")
                        node_name = getattr(addr, "node_name", "")
                        target_ref = None
                        ref = getattr(addr, "target_ref", None)
                        if ref:
                            target_ref = {
                                "kind": getattr(ref, "kind", ""),
                                "name": getattr(ref, "name", ""),
                                "namespace": getattr(ref, "namespace", ""),
                            }
                        not_ready_addresses.append({
                            "ip": ip,
                            "node_name": node_name,
                            "target_ref": target_ref
                        })

                    # Ports
                    for p in (getattr(sub, "ports", []) or []):
                        ports.append({
                            "name": getattr(p, "name", ""),
                            "port": getattr(p, "port", 0),
                            "protocol": getattr(p, "protocol", "TCP"),
                        })

                ep_info = {
                    "service_name": svc_name,
                    "namespace": namespace,
                    "ready_addresses_count": len(ready_addresses),
                    "not_ready_addresses_count": len(not_ready_addresses),
                    "ready_addresses": ready_addresses,
                    "not_ready_addresses": not_ready_addresses,
                    "ports": ports,
                }
                endpoints_list.append(ep_info)

                # Findings
                if len(ready_addresses) == 0:
                    findings.append({
                        "severity": "CRITICAL",
                        "category": "ENDPOINT",
                        "message": f"Service '{svc_name}' has 0 ready endpoints. Traffic to this service will fail.",
                        "evidence": [f"service: {svc_name}", f"ready_addresses: 0", f"not_ready_addresses: {len(not_ready_addresses)}"]
                    })

                if pod_ip:
                    pod_in_not_ready = any(a["ip"] == pod_ip for a in not_ready_addresses)
                    if pod_in_not_ready:
                        findings.append({
                            "severity": "WARNING",
                            "category": "ENDPOINT",
                            "message": f"Pod IP '{pod_ip}' is marked as NOT READY in endpoints for Service '{svc_name}'",
                            "evidence": [f"service: {svc_name}", f"pod_ip: {pod_ip}"]
                        })

            except Exception as e:
                logger.warning(f"Could not read endpoints for service {namespace}/{svc_name}: {e}")
                findings.append({
                    "severity": "WARNING",
                    "category": "ENDPOINT",
                    "message": f"Could not retrieve Endpoints for Service '{svc_name}': {e}",
                    "evidence": [str(e)]
                })

        return endpoints_list, findings
