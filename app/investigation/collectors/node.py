import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("SkyOps.NodeCollector")


class NodeCollector:
    """
    Collects Node status, conditions, capacity, allocatable resources, system info,
    and checks node health for the node hosting an affected Pod.
    """

    @staticmethod
    def collect(
        v1_api: Any,
        node_name: str,
        pod_name: str,
        namespace: str
    ) -> Tuple[Dict[str, Any], List[Dict[str, str]], List[Dict[str, Any]]]:
        """
        Returns: (node_info, relationships, findings)
        """
        node_info = {}
        relationships = []
        findings = []

        if not v1_api or not node_name:
            return node_info, relationships, findings

        # Relationship
        relationships.append({
            "from": f"Pod/{namespace}/{pod_name}",
            "relationship": "SCHEDULED_ON",
            "to": f"Node/{node_name}"
        })

        try:
            node = v1_api.read_node(name=node_name)
            meta = getattr(node, "metadata", None)
            status = getattr(node, "status", None)
            spec = getattr(node, "spec", None)

            conditions = {}
            if status and hasattr(status, "conditions") and status.conditions:
                for cond in status.conditions:
                    c_type = getattr(cond, "type", "")
                    c_status = getattr(cond, "status", "")
                    conditions[c_type] = {
                        "status": c_status,
                        "reason": getattr(cond, "reason", ""),
                        "message": getattr(cond, "message", ""),
                    }

            node_info = {
                "name": getattr(meta, "name", node_name) if meta else node_name,
                "uid": getattr(meta, "uid", "") if meta else "",
                "creation_timestamp": str(getattr(meta, "creation_timestamp", "")) if meta else "",
                "labels": getattr(meta, "labels", {}) or {} if meta else {},
                "conditions": conditions,
                "ready": conditions.get("Ready", {}).get("status") == "True",
                "memory_pressure": conditions.get("MemoryPressure", {}).get("status") == "True",
                "disk_pressure": conditions.get("DiskPressure", {}).get("status") == "True",
                "pid_pressure": conditions.get("PIDPressure", {}).get("status") == "True",
                "network_unavailable": conditions.get("NetworkUnavailable", {}).get("status") == "True",
                "unschedulable": getattr(spec, "unschedulable", False) if spec else False,
                "taints": [
                    {
                        "key": getattr(t, "key", ""),
                        "value": getattr(t, "value", ""),
                        "effect": getattr(t, "effect", ""),
                    } for t in (getattr(spec, "taints", []) or [])
                ] if spec else [],
                "capacity": getattr(status, "capacity", {}) or {} if status else {},
                "allocatable": getattr(status, "allocatable", {}) or {} if status else {},
            }

            node_sys_info = getattr(status, "node_info", None) if status else None
            if node_sys_info:
                node_info["node_info"] = {
                    "kubelet_version": getattr(node_sys_info, "kubelet_version", ""),
                    "os_image": getattr(node_sys_info, "os_image", ""),
                    "architecture": getattr(node_sys_info, "architecture", ""),
                    "container_runtime_version": getattr(node_sys_info, "container_runtime_version", ""),
                    "operating_system": getattr(node_sys_info, "operating_system", ""),
                    "kernel_version": getattr(node_sys_info, "kernel_version", ""),
                }

            # Findings
            if not node_info.get("ready"):
                findings.append({
                    "severity": "CRITICAL",
                    "category": "NODE",
                    "message": f"Node '{node_name}' hosting pod '{pod_name}' is NOT READY",
                    "evidence": [f"Ready condition: {conditions.get('Ready')}"]
                })

            if node_info.get("memory_pressure"):
                findings.append({
                    "severity": "CRITICAL",
                    "category": "NODE",
                    "message": f"Node '{node_name}' is under MemoryPressure",
                    "evidence": ["MemoryPressure: True"]
                })

            if node_info.get("disk_pressure"):
                findings.append({
                    "severity": "CRITICAL",
                    "category": "NODE",
                    "message": f"Node '{node_name}' is under DiskPressure",
                    "evidence": ["DiskPressure: True"]
                })

            if node_info.get("unschedulable"):
                findings.append({
                    "severity": "WARNING",
                    "category": "NODE",
                    "message": f"Node '{node_name}' is marked unschedulable (cordoned)",
                    "evidence": ["unschedulable: True"]
                })

        except Exception as e:
            logger.warning(f"Could not read Node '{node_name}': {e}")
            findings.append({
                "severity": "WARNING",
                "category": "NODE",
                "message": f"Could not inspect Node '{node_name}': {e}",
                "evidence": [str(e)]
            })

        return node_info, relationships, findings
