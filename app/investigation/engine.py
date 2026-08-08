import logging
from typing import Any, Dict, List, Optional
from kubernetes import client

from app.incidents.models import Incident
from app.investigation.models import InvestigationResult
from app.investigation.collectors.pod import PodCollector
from app.investigation.collectors.controller import ControllerCollector
from app.investigation.collectors.replicaset import ReplicaSetCollector
from app.investigation.collectors.deployment import DeploymentCollector
from app.investigation.collectors.service import ServiceCollector
from app.investigation.collectors.endpoints import EndpointsCollector
from app.investigation.collectors.node import NodeCollector
from app.investigation.collectors.storage import StorageCollector
from app.investigation.collectors.events import EventsCollector

logger = logging.getLogger("SkyOps.InvestigationEngine")


class InvestigationEngine:
    """
    Coordinates multi-dimensional Kubernetes evidence collection across Pods,
    Controllers, Services, Endpoints, Nodes, Storage, and Events.
    Runs collectors with failure isolation (partial failure resilience).
    """

    def __init__(
        self,
        v1_api: Optional[client.CoreV1Api] = None,
        apps_v1_api: Optional[client.AppsV1Api] = None,
        storage_v1_api: Optional[client.StorageV1Api] = None,
    ):
        self.v1_api = v1_api
        self.apps_v1_api = apps_v1_api
        self.storage_v1_api = storage_v1_api

    def investigate(self, incident: Incident, pod_obj: Optional[Any] = None) -> InvestigationResult:
        """
        Runs deep investigation for the given Incident.
        """
        incident_id = incident.incident_id
        namespace = incident.resource.namespace or "default"
        pod_name = incident.resource.name

        target = {
            "kind": incident.resource.kind or "Pod",
            "name": pod_name,
            "namespace": namespace,
            "uid": incident.resource.uid,
        }

        collector_status: Dict[str, str] = {}
        all_relationships: List[Dict[str, str]] = []
        all_findings: List[Dict[str, Any]] = []

        pod_info: Dict[str, Any] = {}
        configmaps_ref: List[Dict[str, Any]] = []
        secrets_ref: List[Dict[str, Any]] = []
        controllers: List[Dict[str, Any]] = []
        replicaset_info: Dict[str, Any] = {}
        deployment_info: Dict[str, Any] = {}
        services_info: List[Dict[str, Any]] = []
        endpoints_info: List[Dict[str, Any]] = []
        node_info: Dict[str, Any] = {}
        storage_info: Dict[str, Any] = {}
        events_list: List[Dict[str, Any]] = []

        involved_objects = [{"kind": "Pod", "name": pod_name}]

        # -------------------------------------------------------------
        # 1. POD COLLECTOR
        # -------------------------------------------------------------
        try:
            pod_info, configmaps_ref, secrets_ref, p_findings = PodCollector.collect(
                self.v1_api, namespace, pod_name, pod_obj=pod_obj
            )
            all_findings.extend(p_findings)
            collector_status["pod"] = "SUCCESS"
        except Exception as e:
            logger.error(f"Pod collector failed for {namespace}/{pod_name}: {e}")
            collector_status["pod"] = f"FAILED: {e}"
            all_findings.append({
                "severity": "CRITICAL",
                "category": "POD",
                "message": f"Pod collector failed: {e}",
                "evidence": [str(e)]
            })

        # -------------------------------------------------------------
        # 2. CONTROLLER COLLECTOR
        # -------------------------------------------------------------
        owner_refs = pod_info.get("owner_references", [])
        try:
            controllers, ctrl_rels, ctrl_findings = ControllerCollector.collect(
                self.apps_v1_api, namespace, owner_refs, pod_name
            )
            all_relationships.extend(ctrl_rels)
            all_findings.extend(ctrl_findings)
            collector_status["controller"] = "SUCCESS"
        except Exception as e:
            logger.error(f"Controller collector failed for {namespace}/{pod_name}: {e}")
            collector_status["controller"] = f"FAILED: {e}"

        # -------------------------------------------------------------
        # 3. REPLICASET COLLECTOR
        # -------------------------------------------------------------
        rs_name = next((c["name"] for c in controllers if c.get("kind") == "ReplicaSet"), None)
        if rs_name:
            involved_objects.append({"kind": "ReplicaSet", "name": rs_name})
            try:
                replicaset_info, rs_findings = ReplicaSetCollector.collect(
                    self.apps_v1_api, namespace, rs_name
                )
                all_findings.extend(rs_findings)
                collector_status["replicaset"] = "SUCCESS"
            except Exception as e:
                logger.error(f"ReplicaSet collector failed for {namespace}/{rs_name}: {e}")
                collector_status["replicaset"] = f"FAILED: {e}"

        # -------------------------------------------------------------
        # 4. DEPLOYMENT COLLECTOR
        # -------------------------------------------------------------
        dep_name = next((c["name"] for c in controllers if c.get("kind") == "Deployment"), None)
        if dep_name:
            involved_objects.append({"kind": "Deployment", "name": dep_name})
            try:
                deployment_info, dep_findings = DeploymentCollector.collect(
                    self.apps_v1_api, namespace, dep_name
                )
                all_findings.extend(dep_findings)
                collector_status["deployment"] = "SUCCESS"
            except Exception as e:
                logger.error(f"Deployment collector failed for {namespace}/{dep_name}: {e}")
                collector_status["deployment"] = f"FAILED: {e}"

        # -------------------------------------------------------------
        # 5. SERVICE COLLECTOR (Finds ALL matching services)
        # -------------------------------------------------------------
        pod_labels = pod_info.get("labels", {})
        try:
            services_info, svc_rels, svc_findings = ServiceCollector.collect(
                self.v1_api, namespace, pod_name, pod_labels
            )
            all_relationships.extend(svc_rels)
            all_findings.extend(svc_findings)
            collector_status["service"] = "SUCCESS"
        except Exception as e:
            logger.error(f"Service collector failed for {namespace}/{pod_name}: {e}")
            collector_status["service"] = f"FAILED: {e}"

        # -------------------------------------------------------------
        # 6. ENDPOINTS COLLECTOR
        # -------------------------------------------------------------
        pod_ip = pod_info.get("pod_ip", "")
        if services_info:
            try:
                endpoints_info, ep_findings = EndpointsCollector.collect(
                    self.v1_api, namespace, services_info, pod_ip=pod_ip
                )
                all_findings.extend(ep_findings)
                collector_status["endpoints"] = "SUCCESS"
            except Exception as e:
                logger.error(f"Endpoints collector failed for {namespace}/{pod_name}: {e}")
                collector_status["endpoints"] = f"FAILED: {e}"

        # -------------------------------------------------------------
        # 7. NODE COLLECTOR
        # -------------------------------------------------------------
        node_name = pod_info.get("node_name", "")
        if node_name:
            involved_objects.append({"kind": "Node", "name": node_name})
            try:
                node_info, node_rels, node_findings = NodeCollector.collect(
                    self.v1_api, node_name, pod_name, namespace
                )
                all_relationships.extend(node_rels)
                all_findings.extend(node_findings)
                collector_status["node"] = "SUCCESS"
            except Exception as e:
                logger.error(f"Node collector failed for node '{node_name}': {e}")
                collector_status["node"] = f"FAILED: {e}"

        # -------------------------------------------------------------
        # 8. STORAGE COLLECTOR
        # -------------------------------------------------------------
        pod_volumes = pod_info.get("volumes", [])
        if pod_volumes:
            try:
                storage_info, st_rels, st_findings = StorageCollector.collect(
                    self.v1_api, self.storage_v1_api, namespace, pod_name, pod_volumes
                )
                all_relationships.extend(st_rels)
                all_findings.extend(st_findings)
                collector_status["storage"] = "SUCCESS"

                for pvc_item in storage_info.get("pvcs", []):
                    if pvc_item.get("name"):
                        involved_objects.append({"kind": "PersistentVolumeClaim", "name": pvc_item["name"]})

            except Exception as e:
                logger.error(f"Storage collector failed for pod {namespace}/{pod_name}: {e}")
                collector_status["storage"] = f"FAILED: {e}"

        # -------------------------------------------------------------
        # 9. EVENTS COLLECTOR
        # -------------------------------------------------------------
        try:
            events_list = EventsCollector.collect(self.v1_api, namespace, involved_objects)
            collector_status["events"] = "SUCCESS"
        except Exception as e:
            logger.error(f"Events collector failed for {namespace}/{pod_name}: {e}")
            collector_status["events"] = f"FAILED: {e}"

        # Deduplicate relationships and findings
        unique_rels = []
        rel_seen = set()
        for r in all_relationships:
            key = f"{r.get('from')}->{r.get('relationship')}->{r.get('to')}"
            if key not in rel_seen:
                rel_seen.add(key)
                unique_rels.append(r)

        unique_findings = []
        finding_seen = set()
        for f in all_findings:
            key = f"{f.get('category')}:{f.get('message')}"
            if key not in finding_seen:
                finding_seen.add(key)
                unique_findings.append(f)

        result = InvestigationResult(
            incident_id=incident_id,
            target=target,
            pod=pod_info,
            controllers=controllers,
            deployment=deployment_info,
            replicaset=replicaset_info,
            services=services_info,
            service=services_info[0] if services_info else {},
            endpoints=endpoints_info,
            node=node_info,
            storage=storage_info,
            configmaps=configmaps_ref,
            secrets=secrets_ref,  # METADATA ONLY!
            events=events_list,
            relationships=unique_rels,
            findings=unique_findings,
            collector_status=collector_status,
        )

        return result

    @staticmethod
    def print_investigation_summary(result: InvestigationResult) -> None:
        """
        Prints formatted human-readable investigation summary to stdout.
        """
        print("\n============================================================")
        print(f"🔍 DEEP INVESTIGATION RESULT — {result.incident_id}")
        print("============================================================")
        print(f"Target: {result.target.get('namespace')}/{result.target.get('name')} ({result.target.get('kind')})")

        # Pod State
        pod = result.pod
        print(f"\n📦 Pod State:")
        print(f"  Phase: {pod.get('phase', 'Unknown')}")
        print(f"  Node: {pod.get('node_name', 'Unassigned')}")
        print(f"  IP: {pod.get('pod_ip', 'None')}")

        containers = pod.get("containers", [])
        if containers:
            print("  Containers:")
            for c in containers:
                st = c.get("state", "unknown")
                detail = c.get("state_detail", {})
                restarts = c.get("restart_count", 0)
                print(f"    - {c.get('name')}: {st} (restarts: {restarts})")
                if detail:
                    reason = detail.get("reason", "")
                    msg = detail.get("message", "")
                    if reason or msg:
                        print(f"      Detail: {reason} {msg}")

        # Controllers
        if result.deployment:
            dep = result.deployment
            print(f"\n🚀 Deployment: {dep.get('name')}")
            print(f"  Replicas: {dep.get('ready_replicas', 0)}/{dep.get('desired_replicas', 0)} ready")

        if result.replicaset:
            rs = result.replicaset
            print(f"  ReplicaSet: {rs.get('name')} ({rs.get('ready_replicas', 0)}/{rs.get('desired_replicas', 0)} ready)")

        # Services & Endpoints
        if result.services:
            print(f"\n🌐 Services ({len(result.services)}):")
            for svc in result.services:
                print(f"  - {svc.get('name')} ({svc.get('type')}, ClusterIP: {svc.get('cluster_ip')})")

        if result.endpoints:
            print("  Endpoints:")
            for ep in result.endpoints:
                print(f"    - {ep.get('service_name')}: {ep.get('ready_addresses_count', 0)} ready, {ep.get('not_ready_addresses_count', 0)} not ready")

        # Node
        if result.node:
            node = result.node
            sys_info = node.get("node_info", {})
            print(f"\n🖥️ Node: {node.get('name')}")
            print(f"  Ready: {node.get('ready')}")
            print(f"  MemoryPressure: {node.get('memory_pressure')}, DiskPressure: {node.get('disk_pressure')}")
            if sys_info:
                print(f"  Kubelet: {sys_info.get('kubelet_version')}, Runtime: {sys_info.get('container_runtime_version')}")

        # Storage
        if result.storage and (result.storage.get("pvcs") or result.storage.get("pvs")):
            print(f"\n💾 Storage:")
            for pvc in result.storage.get("pvcs", []):
                print(f"  PVC: {pvc.get('name')} (Phase: {pvc.get('phase')}, StorageClass: {pvc.get('storage_class')})")
            for pv in result.storage.get("pvs", []):
                print(f"  PV: {pv.get('name')} (Phase: {pv.get('phase')})")

        # Secret references metadata check
        if result.secrets:
            print(f"\n🔒 Referenced Secrets (Metadata only):")
            for sec in result.secrets:
                print(f"  - {sec.get('name')} (namespace: {sec.get('namespace')})")

        # Relationships
        if result.relationships:
            print(f"\n🔗 Relationships ({len(result.relationships)}):")
            for r in result.relationships:
                print(f"  {r.get('from')} --[{r.get('relationship')}]--> {r.get('to')}")

        # Findings
        if result.findings:
            print(f"\n💡 Findings ({len(result.findings)}):")
            for f in result.findings:
                sev = f.get("severity", "INFO")
                print(f"  [{sev}] [{f.get('category')}] {f.get('message')}")

        print("============================================================\n")
