import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from kubernetes import client
from kubernetes.client.rest import ApiException

from app.config import AGENT_NAMESPACE, CLUSTER_ID_FILE, CLUSTER_NAME

logger = logging.getLogger("SkyOps.ClusterManager")

CONFIGMAP_NAME = "skyops-cluster-info"


def get_or_create_cluster_id(
    v1_client: Optional[client.CoreV1Api] = None,
    namespace: str = AGENT_NAMESPACE,
) -> str:
    """
    Retrieves or generates a persistent cluster_id for the SkyOps agent.
    First attempts to store/read from a Kubernetes ConfigMap ('skyops-cluster-info').
    Falls back to local file storage if in local dev mode or if K8s API fails.
    """
    # 1. Try In-Cluster ConfigMap persistence
    if v1_client is not None:
        try:
            try:
                cm = v1_client.read_namespaced_config_map(CONFIGMAP_NAME, namespace)
                if cm.data and "cluster_id" in cm.data:
                    cluster_id = cm.data["cluster_id"]
                    logger.info(f"Loaded cluster_id from K8s ConfigMap '{CONFIGMAP_NAME}': {cluster_id}")
                    return cluster_id
            except ApiException as e:
                if e.status == 404:
                    # ConfigMap does not exist, create it
                    new_id = f"skyops-cluster-{uuid.uuid4()}"
                    now_iso = datetime.now(timezone.utc).isoformat()
                    body = client.V1ConfigMap(
                        metadata=client.V1ObjectMeta(
                            name=CONFIGMAP_NAME,
                            namespace=namespace,
                            labels={"app.kubernetes.io/managed-by": "skyops-agent"},
                        ),
                        data={"cluster_id": new_id, "created_at": now_iso},
                    )
                    try:
                        v1_client.create_namespaced_config_map(namespace, body)
                        logger.info(f"Created K8s ConfigMap '{CONFIGMAP_NAME}' with cluster_id: {new_id}")
                        return new_id
                    except ApiException as create_err:
                        logger.warning(f"Could not create ConfigMap '{CONFIGMAP_NAME}': {create_err}")
                else:
                    logger.warning(f"Could not read ConfigMap '{CONFIGMAP_NAME}': {e}")
        except Exception as ex:
            logger.warning(f"Failed to access ConfigMap for cluster ID: {ex}")

    # 2. Fallback to Local File Persistence
    try:
        if CLUSTER_ID_FILE.exists():
            cid = CLUSTER_ID_FILE.read_text(encoding="utf-8").strip()
            if cid:
                logger.info(f"Loaded cluster_id from local file: {cid}")
                return cid
        
        # Generate new file-backed cluster_id
        CLUSTER_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        new_id = f"skyops-cluster-{uuid.uuid4()}"
        CLUSTER_ID_FILE.write_text(new_id, encoding="utf-8")
        logger.info(f"Generated new persistent cluster_id: {new_id}")
        return new_id
    except Exception as file_ex:
        logger.warning(f"Could not read/write local cluster_id file: {file_ex}")
        return f"skyops-cluster-{uuid.uuid4()}"


def collect_cluster_info(
    v1_client: Optional[client.CoreV1Api] = None,
    api_client: Optional[client.ApiClient] = None,
    cluster_id: str = "unknown",
) -> Dict[str, Any]:
    """
    Collects basic metadata about the connected Kubernetes cluster.
    """
    info = {
        "cluster_id": cluster_id,
        "cluster_name": CLUSTER_NAME if CLUSTER_NAME != "default-cluster" else "unknown",
        "kubernetes_version": "unknown",
        "nodes": 0,
        "namespaces": 0,
        "pods": 0,
        "node_names": [],
        "node_readiness": {},
    }

    if not v1_client:
        return info

    # 1. Kubernetes Server Version
    try:
        version_api = client.VersionApi(api_client) if api_client else None
        if version_api:
            v_info = version_api.get_code()
            info["kubernetes_version"] = v_info.git_version
    except Exception as e:
        logger.debug(f"Could not fetch K8s version: {e}")

    # 2. Nodes & Readiness
    try:
        nodes = v1_client.list_node().items
        info["nodes"] = len(nodes)
        node_names = []
        node_readiness = {}
        for n in nodes:
            name = n.metadata.name
            node_names.append(name)
            is_ready = "Unknown"
            if n.status and n.status.conditions:
                for cond in n.status.conditions:
                    if cond.type == "Ready":
                        is_ready = "Ready" if cond.status == "True" else "NotReady"
                        break
            node_readiness[name] = is_ready

        info["node_names"] = node_names
        info["node_readiness"] = node_readiness
    except Exception as e:
        logger.debug(f"Could not list nodes: {e}")

    # 3. Namespaces
    try:
        ns_list = v1_client.list_namespace().items
        info["namespaces"] = len(ns_list)
    except Exception as e:
        logger.debug(f"Could not list namespaces: {e}")

    # 4. Pods
    try:
        pods = v1_client.list_pod_for_all_namespaces().items
        info["pods"] = len(pods)
    except Exception as e:
        logger.debug(f"Could not list pods for all namespaces: {e}")

    return info
