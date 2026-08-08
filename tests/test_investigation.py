import pytest
from types import SimpleNamespace
from app.incidents.models import Incident, ResourceRef
from app.investigation.engine import InvestigationEngine
from app.investigation.models import InvestigationResult
from app.investigation.collectors.pod import PodCollector
from app.investigation.collectors.controller import ControllerCollector
from app.investigation.collectors.service import ServiceCollector
from app.investigation.collectors.endpoints import EndpointsCollector
from app.investigation.collectors.node import NodeCollector
from app.investigation.collectors.storage import StorageCollector


def create_mock_pod(name="test-pod", namespace="default", phase="Pending", reason="ErrImagePull"):
    pod = SimpleNamespace()
    pod.metadata = SimpleNamespace(
        name=name,
        namespace=namespace,
        uid=f"uid-{name}",
        creation_timestamp="2026-08-08T00:00:00Z",
        labels={"app": "web", "tier": "frontend"},
        annotations={},
        owner_references=[
            SimpleNamespace(kind="ReplicaSet", name=f"{name}-rs-123", uid=f"uid-rs-123", controller=True)
        ]
    )
    c_state = SimpleNamespace(
        running=None,
        waiting=SimpleNamespace(reason=reason, message="Failed to pull image"),
        terminated=None
    )
    c_status = SimpleNamespace(
        name="app",
        image="broken-image:latest",
        image_id="",
        ready=False,
        restart_count=0,
        state=c_state
    )
    volume = SimpleNamespace(
        name="data-vol",
        persistent_volume_claim=SimpleNamespace(claim_name="pvc-data"),
        config_map=None,
        secret=None,
        host_path=None,
        empty_dir=None
    )
    pod.spec = SimpleNamespace(
        node_name="node-1",
        containers=[SimpleNamespace(name="app", image="broken-image:latest", env=[], env_from=[])],
        init_containers=[],
        volumes=[volume]
    )
    pod.status = SimpleNamespace(
        phase=phase,
        pod_ip="10.244.1.15",
        host_ip="192.168.1.100",
        node_name="node-1",
        start_time="2026-08-08T00:00:00Z",
        container_statuses=[c_status],
        init_container_statuses=[],
        conditions=[]
    )
    return pod


def test_pod_collector():
    pod = create_mock_pod()
    pod_info, cm_ref, sec_ref, findings = PodCollector.collect(
        v1_api=None, namespace="default", pod_name="test-pod", pod_obj=pod
    )

    assert pod_info["name"] == "test-pod"
    assert pod_info["phase"] == "Pending"
    assert pod_info["pod_ip"] == "10.244.1.15"
    assert len(pod_info["containers"]) == 1
    assert pod_info["containers"][0]["state"] == "waiting"
    assert len(findings) > 0
    assert any("broken-image:latest" in str(f) for f in findings)


def test_controller_collector():
    owner_refs = [
        {"kind": "ReplicaSet", "name": "web-rs-123", "uid": "uid-rs"}
    ]
    controllers, rels, findings = ControllerCollector.collect(
        apps_v1_api=None, namespace="default", owner_references=owner_refs, pod_name="web-pod"
    )

    assert len(controllers) == 1
    assert controllers[0]["kind"] == "ReplicaSet"
    assert len(rels) == 1
    assert rels[0]["relationship"] == "OWNED_BY"
    assert rels[0]["from"] == "Pod/default/web-pod"
    assert rels[0]["to"] == "ReplicaSet/default/web-rs-123"


def test_investigation_engine_full_run():
    pod = create_mock_pod()
    incident = Incident(
        incident_id="INC-1001",
        status="OPEN",
        resource=ResourceRef(kind="Pod", name="test-pod", namespace="default", uid="uid-test-pod"),
        category="ImagePullFailure",
        current_state="ErrImagePull",
    )

    engine = InvestigationEngine(v1_api=None, apps_v1_api=None, storage_v1_api=None)
    result = engine.investigate(incident, pod_obj=pod)

    assert isinstance(result, InvestigationResult)
    assert result.incident_id == "INC-1001"
    assert result.pod["name"] == "test-pod"
    assert len(result.findings) > 0
    assert result.collector_status["pod"] == "SUCCESS"
    assert result.collector_status["controller"] == "SUCCESS"
