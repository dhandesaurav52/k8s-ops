import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace
from app.incidents.models import Incident, ResourceRef
from app.investigation.engine import InvestigationEngine


def test_investigation_partial_failure_resilience():
    # Mock CoreV1Api where list_namespaced_service raises an API exception
    mock_v1 = MagicMock()
    mock_v1.list_namespaced_service.side_effect = Exception("Service API Endpoint Unavailable (503)")
    mock_v1.read_node.side_effect = Exception("Node API Permission Denied (403)")

    pod = SimpleNamespace()
    pod.metadata = SimpleNamespace(
        name="partial-fail-pod",
        namespace="default",
        uid="uid-partial",
        creation_timestamp="2026-08-08T00:00:00Z",
        labels={"app": "api"},
        annotations={},
        owner_references=[]
    )
    c_state = SimpleNamespace(
        running=None,
        waiting=SimpleNamespace(reason="ErrImagePull", message="Image not found"),
        terminated=None
    )
    c_status = SimpleNamespace(
        name="app",
        image="broken:latest",
        image_id="",
        ready=False,
        restart_count=0,
        state=c_state
    )
    pod.spec = SimpleNamespace(
        node_name="node-broken",
        containers=[SimpleNamespace(name="app", image="broken:latest", env=[], env_from=[])],
        init_containers=[],
        volumes=[]
    )
    pod.status = SimpleNamespace(
        phase="Pending",
        pod_ip="",
        host_ip="",
        node_name="node-broken",
        start_time="",
        container_statuses=[c_status],
        init_container_statuses=[],
        conditions=[]
    )

    incident = Incident(
        incident_id="INC-PARTIAL-1",
        status="OPEN",
        resource=ResourceRef(kind="Pod", name="partial-fail-pod", namespace="default", uid="uid-partial"),
        category="ImagePullFailure",
        current_state="ErrImagePull",
    )

    engine = InvestigationEngine(v1_api=mock_v1, apps_v1_api=None, storage_v1_api=None)
    result = engine.investigate(incident, pod_obj=pod)

    # Investigation succeeds with partial results!
    assert result.pod["name"] == "partial-fail-pod"
    assert result.collector_status["pod"] == "SUCCESS"
    # Service and Node collectors recorded error findings
    assert "service" in result.collector_status or len(result.findings) > 0
