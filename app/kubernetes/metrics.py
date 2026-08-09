import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from kubernetes import client
from kubernetes.client.rest import ApiException

logger = logging.getLogger("SkyOps.MetricsCollector")


def parse_cpu_to_mcores(cpu_str: str) -> float:
    """
    Parses a Kubernetes CPU quantity string to millicores (m).
    Examples:
      '250m' -> 250.0
      '150000000n' -> 150.0
      '2' -> 2000.0
      '0.5' -> 500.0
    """
    if not cpu_str:
        return 0.0
    
    cpu_str = str(cpu_str).strip()
    if cpu_str.endswith("n"):
        try:
            return float(cpu_str[:-1]) / 1_000_000.0
        except ValueError:
            return 0.0
    elif cpu_str.endswith("u"):
        try:
            return float(cpu_str[:-1]) / 1_000.0
        except ValueError:
            return 0.0
    elif cpu_str.endswith("m"):
        try:
            return float(cpu_str[:-1])
        except ValueError:
            return 0.0
    else:
        try:
            return float(cpu_str) * 1000.0
        except ValueError:
            return 0.0


def parse_memory_to_mb(mem_str: str) -> float:
    """
    Parses a Kubernetes memory quantity string to Megabytes (MB).
    Examples:
      '512Mi' -> 512.0
      '1Gi' -> 1024.0
      '524288Ki' -> 512.0
      '1073741824' -> 1024.0
    """
    if not mem_str:
        return 0.0
    
    mem_str = str(mem_str).strip()
    try:
        if mem_str.endswith("Ki"):
            return float(mem_str[:-2]) / 1024.0
        elif mem_str.endswith("Mi"):
            return float(mem_str[:-2])
        elif mem_str.endswith("Gi"):
            return float(mem_str[:-2]) * 1024.0
        elif mem_str.endswith("Ti"):
            return float(mem_str[:-2]) * 1024.0 * 1024.0
        elif mem_str.endswith("k"):
            return (float(mem_str[:-1]) * 1000.0) / (1024.0 * 1024.0)
        elif mem_str.endswith("M"):
            return (float(mem_str[:-1]) * 1000.0 * 1000.0) / (1024.0 * 1024.0)
        elif mem_str.endswith("G"):
            return (float(mem_str[:-1]) * 1000.0 * 1000.0 * 1000.0) / (1024.0 * 1024.0)
        else:
            return float(mem_str) / (1024.0 * 1024.0)
    except ValueError:
        return 0.0


def collect_node_capacities(v1_client: client.CoreV1Api) -> Dict[str, Dict[str, float]]:
    """
    Collects node CPU & Memory capacity and allocatable specs via CoreV1Api.
    """
    capacities = {}
    try:
        nodes = v1_client.list_node().items
        for node in nodes:
            name = node.metadata.name
            alloc = node.status.allocatable or {}
            cap = node.status.capacity or {}

            cpu_alloc = parse_cpu_to_mcores(alloc.get("cpu", cap.get("cpu", "0")))
            mem_alloc = parse_memory_to_mb(alloc.get("memory", cap.get("memory", "0")))

            conditions = {}
            if node.status and node.status.conditions:
                for cond in node.status.conditions:
                    conditions[cond.type] = cond.status

            capacities[name] = {
                "cpu_capacity_mcores": cpu_alloc,
                "memory_capacity_mb": mem_alloc,
                "status": "Ready" if conditions.get("Ready") == "True" else "NotReady",
                "conditions": conditions,
            }
    except Exception as e:
        logger.warning(f"Failed to fetch node capacities from CoreV1Api: {e}")
    return capacities


def collect_cluster_metrics(
    api_client: client.ApiClient,
    v1_client: client.CoreV1Api,
    cluster_id: str,
) -> Dict[str, Any]:
    """
    Collects real-time CPU and Memory metrics from metrics.k8s.io API via CustomObjectsApi.
    Returns structured metric summary, node metrics, and pod metrics.
    If metrics-server is unavailable, handles gracefully with status UNAVAILABLE.
    """
    custom_api = client.CustomObjectsApi(api_client)
    node_capacities = collect_node_capacities(v1_client)

    node_metrics_list: List[Dict[str, Any]] = []
    pod_metrics_list: List[Dict[str, Any]] = []
    metrics_available = False
    status_message = "Metrics collected successfully via metrics.k8s.io"

    # 1. Collect Node Usage Metrics
    try:
        raw_node_metrics = custom_api.list_cluster_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            plural="nodes",
        )
        items = raw_node_metrics.get("items", [])
        metrics_available = True

        for item in items:
            name = item.get("metadata", {}).get("name", "unknown")
            usage = item.get("usage", {})
            cpu_mcores = parse_cpu_to_mcores(usage.get("cpu", "0"))
            mem_mb = parse_memory_to_mb(usage.get("memory", "0"))

            cap = node_capacities.get(name, {
                "cpu_capacity_mcores": 4000.0,
                "memory_capacity_mb": 16384.0,
                "status": "Ready",
                "conditions": {},
            })

            cpu_cap = cap["cpu_capacity_mcores"]
            mem_cap = cap["memory_capacity_mb"]

            cpu_pct = round((cpu_mcores / cpu_cap) * 100.0, 1) if cpu_cap > 0 else 0.0
            mem_pct = round((mem_mb / mem_cap) * 100.0, 1) if mem_cap > 0 else 0.0

            node_metrics_list.append({
                "name": name,
                "cluster_id": cluster_id,
                "cpu_usage_mcores": round(cpu_mcores, 1),
                "cpu_capacity_mcores": round(cpu_cap, 1),
                "cpu_pct": cpu_pct,
                "memory_usage_mb": round(mem_mb, 1),
                "memory_capacity_mb": round(mem_cap, 1),
                "memory_pct": mem_pct,
                "status": cap["status"],
                "conditions": cap["conditions"],
            })
    except ApiException as ae:
        if ae.status == 404:
            status_message = "metrics.k8s.io API not found. Deploy metrics-server to enable real cluster resource metrics."
            logger.info("metrics.k8s.io not available on this Kubernetes cluster.")
        else:
            status_message = f"Metrics API returned HTTP {ae.status}: {ae.reason}"
            logger.warning(f"Error fetching node metrics: {ae}")
    except Exception as e:
        status_message = f"Error connecting to metrics.k8s.io: {e}"
        logger.warning(f"Unexpected error fetching node metrics: {e}")

    # 2. Collect Pod Usage Metrics if available
    if metrics_available:
        try:
            raw_pod_metrics = custom_api.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="pods",
            )
            p_items = raw_pod_metrics.get("items", [])
            for pitem in p_items:
                meta = pitem.get("metadata", {})
                pod_name = meta.get("name", "unknown")
                ns = meta.get("namespace", "default")
                containers = pitem.get("containers", [])

                pod_cpu = 0.0
                pod_mem = 0.0
                for c in containers:
                    c_usage = c.get("usage", {})
                    pod_cpu += parse_cpu_to_mcores(c_usage.get("cpu", "0"))
                    pod_mem += parse_memory_to_mb(c_usage.get("memory", "0"))

                pod_metrics_list.append({
                    "name": pod_name,
                    "namespace": ns,
                    "cluster_id": cluster_id,
                    "cpu_usage_mcores": round(pod_cpu, 1),
                    "memory_usage_mb": round(pod_mem, 1),
                })
        except Exception as pe:
            logger.debug(f"Could not fetch pod metrics: {pe}")

    # 3. Calculate Aggregated Summary
    total_cpu_cap = sum(n["cpu_capacity_mcores"] for n in node_metrics_list)
    total_cpu_used = sum(n["cpu_usage_mcores"] for n in node_metrics_list)
    total_mem_cap = sum(n["memory_capacity_mb"] for n in node_metrics_list)
    total_mem_used = sum(n["memory_usage_mb"] for n in node_metrics_list)

    overall_cpu_pct = round((total_cpu_used / total_cpu_cap) * 100.0, 1) if total_cpu_cap > 0 else 0.0
    overall_mem_pct = round((total_mem_used / total_mem_cap) * 100.0, 1) if total_mem_cap > 0 else 0.0

    return {
        "cluster_id": cluster_id,
        "metrics_status": "ONLINE" if metrics_available else "UNAVAILABLE",
        "status_message": status_message,
        "source": "metrics.k8s.io" if metrics_available else "CoreV1Api (Metrics Unavailable)",
        "summary": {
            "total_cpu_mcores": round(total_cpu_cap, 1),
            "used_cpu_mcores": round(total_cpu_used, 1),
            "cpu_utilization_pct": overall_cpu_pct,
            "total_memory_mb": round(total_mem_cap, 1),
            "used_memory_mb": round(total_mem_used, 1),
            "memory_utilization_pct": overall_mem_pct,
        },
        "nodes": node_metrics_list,
        "pods": pod_metrics_list,
    }
