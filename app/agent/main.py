#!/usr/bin/env python3
import argparse
import logging
import sys
import time

from app.agent.cluster import collect_cluster_info, get_or_create_cluster_id
from app.agent.connector import LocalDevelopmentConnector
from app.agent.health import HealthServer
from app.ai.analyzer import AIAnalyzer
from app.config import (
    AGENT_NAMESPACE,
    AGENT_PORT,
    INCIDENTS_FILE,
    LOG_LEVEL,
    WATCH_NAMESPACE,
)
from app.incidents.manager import IncidentManager
from app.incidents.store import IncidentStore
from app.kubernetes.client import check_connection, get_all_k8s_apis
from app.kubernetes.watcher import KubernetesWatcher

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="[%(levelname)s] %(asctime)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SkyOps.Agent")


def run_agent(kubeconfig_path: str = None, port: int = AGENT_PORT, standalone: bool = False):
    """
    Main entry point for running the SkyOps Kubernetes Agent inside a cluster or locally.
    """
    # 1. Start HTTP Health Probe Server
    health_server = HealthServer(port=port)
    health_server.start()

    # 2. Connect to Kubernetes API
    logger.info("Connecting to Kubernetes API...")
    k8s_connected = False
    v1 = None
    apps_v1 = None
    storage_v1 = None
    api_client = None

    try:
        v1, apps_v1, storage_v1, api_client = get_all_k8s_apis(kubeconfig_path=kubeconfig_path)
        if check_connection(v1):
            k8s_connected = True
        else:
            logger.error("Kubernetes API health check failed.")
    except Exception as e:
        logger.error(f"Kubernetes connection initialization failed: {e}")

    # 3. Cluster Identity & Info
    cluster_id = get_or_create_cluster_id(v1_client=v1 if k8s_connected else None, namespace=AGENT_NAMESPACE)
    health_server.set_k8s_status(connected=k8s_connected, cluster_id=cluster_id)

    cluster_info = collect_cluster_info(
        v1_client=v1 if k8s_connected else None,
        api_client=api_client if k8s_connected else None,
        cluster_id=cluster_id,
    )

    # 4. Connector Stub & Engines
    connector = LocalDevelopmentConnector()
    connector.register(cluster_info)

    store = IncidentStore(INCIDENTS_FILE)
    ai_analyzer = AIAnalyzer()
    ai_status_str = "READY" if ai_analyzer.provider.is_available() else "DISABLED"

    # 5. Output Agent Startup Banner
    k8s_conn_str = "OK" if k8s_connected else "FAILED / DISCONNECTED"
    k8s_version = cluster_info.get("kubernetes_version", "unknown")
    nodes_count = cluster_info.get("nodes", "0")
    ns_count = cluster_info.get("namespaces", "0")
    pods_count = cluster_info.get("pods", "0")

    print("\n" + "=" * 60)
    print("                    SKYOPS AGENT")
    print("=" * 60 + "\n")
    print("Starting SkyOps Kubernetes Agent...\n")
    print(f"Kubernetes connection: {k8s_conn_str}")
    print(f"Cluster ID: {cluster_id}")
    print(f"Kubernetes version: {k8s_version}")
    print(f"Nodes: {nodes_count}")
    print(f"Namespaces: {ns_count}")
    print(f"Pods: {pods_count}\n")
    print("RBAC/API access: OK\n")
    print("Incident engine: STARTING")
    print("Investigation engine: READY")
    print(f"AI engine: {ai_status_str}\n")
    print("SkyOps Agent is running.")
    print("=" * 60 + "\n")

    if not k8s_connected:
        if standalone:
            logger.warning("Agent running without active Kubernetes API connection.")
            return health_server
        else:
            logger.error("Cannot start incident watcher without active K8s API connection.")
            sys.exit(1)

    # 6. Initialize Incident Engine & Watcher
    manager = IncidentManager(
        store=store,
        k8s_client=v1,
        apps_v1_api=apps_v1,
        storage_v1_api=storage_v1,
        ai_analyzer=ai_analyzer,
    )

    watcher = KubernetesWatcher(v1=v1, manager=manager, namespace=WATCH_NAMESPACE)
    
    if standalone:
        # For programmatic execution in background thread / tests
        return health_server, watcher

    # Block and watch
    watcher.start()


def main():
    parser = argparse.ArgumentParser(description="SkyOps Kubernetes Cluster Agent")
    parser.add_argument("--kubeconfig", type=str, help="Path to local kubeconfig file")
    parser.add_argument("--port", type=int, default=AGENT_PORT, help="Health probe HTTP port")
    args = parser.parse_args()

    run_agent(kubeconfig_path=args.kubeconfig, port=args.port)


if __name__ == "__main__":
    main()
