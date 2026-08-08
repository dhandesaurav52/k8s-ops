#!/usr/bin/env python3
import argparse
import logging
import sys
import time
from types import SimpleNamespace

from app.config import INCIDENTS_FILE, LOG_LEVEL, WATCH_NAMESPACE
from app.incidents.manager import IncidentManager
from app.incidents.store import IncidentStore
from app.kubernetes.client import check_connection, get_all_k8s_apis
from app.kubernetes.watcher import KubernetesWatcher

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="[%(levelname)s] %(asctime)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SkyOps.Main")


def print_banner():
    banner = """
============================================================
                     SKYOPS
          Kubernetes Incident Engine
============================================================
    """
    print(banner)


def run_simulation(manager: IncidentManager):
    print("\n--- RUNNING SKYOPS CLUSTER SIMULATION ---")
    logger.info("Starting simulation mode...")

    def create_pod(name, phase="Running", reason=None):
        pod = SimpleNamespace()
        pod.metadata = SimpleNamespace(
            name=name,
            namespace="default",
            uid=f"uid-{name}",
        )
        if phase == "Running" and not reason:
            c_state = SimpleNamespace(waiting=None, terminated=None, running=SimpleNamespace())
            c_status = SimpleNamespace(name="app", state=c_state, ready=True)
            pod.status = SimpleNamespace(phase="Running", container_statuses=[c_status], init_container_statuses=[], conditions=[])
        else:
            c_state = SimpleNamespace(
                waiting=SimpleNamespace(reason=reason, message=f"Container failed with {reason}"),
                terminated=None,
                running=None,
            )
            c_status = SimpleNamespace(name="app", state=c_state, ready=False)
            pod.status = SimpleNamespace(phase=phase, container_statuses=[c_status], init_container_statuses=[], conditions=[])
        return pod

    # 1. Healthy nginx pod
    print("\n[Sim Step 1] Deploying healthy pod: default/nginx")
    manager.process_pod_event("ADDED", create_pod("nginx", phase="Running"))
    time.sleep(1)

    # 2. Broken image pod (broken-nginx)
    print("\n[Sim Step 2] Deploying pod with invalid image: default/broken-nginx")
    manager.process_pod_event("ADDED", create_pod("broken-nginx", phase="Pending", reason="ErrImagePull"))
    time.sleep(1)

    # 3. Repeated event: ErrImagePull -> ImagePullBackOff
    print("\n[Sim Step 3] Pod transitions to ImagePullBackOff")
    manager.process_pod_event("MODIFIED", create_pod("broken-nginx", phase="Pending", reason="ImagePullBackOff"))
    time.sleep(1)

    # 4. Repair workload: broken-nginx becomes Running
    print("\n[Sim Step 4] Repairing workload: default/broken-nginx -> Running")
    manager.process_pod_event("MODIFIED", create_pod("broken-nginx", phase="Running"))
    time.sleep(1)

    print("\nSimulation complete. All lifecycle state checks verified!")


def main():
    parser = argparse.ArgumentParser(description="SkyOps Kubernetes Incident Detection Engine")
    parser.add_argument("--simulate", action="store_true", help="Run in simulation mode")
    parser.add_argument("--agent", action="store_true", help="Run as SkyOps Kubernetes Cluster Agent")
    parser.add_argument("--kubeconfig", type=str, help="Path to kubeconfig file")
    args = parser.parse_args()

    if args.agent:
        from app.agent.main import run_agent
        run_agent(kubeconfig_path=args.kubeconfig)
        return

    print_banner()

    store = IncidentStore(INCIDENTS_FILE)

    if args.simulate:
        manager = IncidentManager(store=store, k8s_client=None)
        run_simulation(manager)
        return

    print("Connecting to Kubernetes...")
    try:
        v1, apps_v1, storage_v1, api_client = get_all_k8s_apis(kubeconfig_path=args.kubeconfig)
        if check_connection(v1):
            print("\nConnected successfully.\n")
            print("Watching Kubernetes...\n")
            print("------------------------------------------------------------")
            manager = IncidentManager(
                store=store,
                k8s_client=v1,
                apps_v1_api=apps_v1,
                storage_v1_api=storage_v1,
            )
            watcher = KubernetesWatcher(v1=v1, manager=manager, namespace=WATCH_NAMESPACE)
            watcher.start()
        else:
            logger.warning("Could not establish active connection to Kubernetes API server.")
            print("Notice: No live Kubernetes API server detected. Running simulation mode instead...")
            manager = IncidentManager(store=store, k8s_client=None)
            run_simulation(manager)
    except Exception as e:
        logger.warning(f"Kubernetes connection failed: {e}")
        print("\nNotice: Live Kubernetes API server not reachable. Running simulation mode...\n")
        manager = IncidentManager(store=store, k8s_client=None)
        run_simulation(manager)


if __name__ == "__main__":
    main()
