import tempfile
from pathlib import Path
from types import SimpleNamespace

from app.incidents.manager import IncidentManager
from app.incidents.store import IncidentStore


def mock_pod(namespace="default", name="test-pod", uid="uid-100", phase="Pending", waiting_reason="ErrImagePull"):
    pod = SimpleNamespace()
    pod.metadata = SimpleNamespace(namespace=namespace, name=name, uid=uid)
    if phase == "Running" and not waiting_reason:
        container_state = SimpleNamespace(waiting=None, terminated=None, running=SimpleNamespace())
        container_status = SimpleNamespace(name="app", state=container_state, ready=True)
        pod.status = SimpleNamespace(phase="Running", container_statuses=[container_status], init_container_statuses=[], conditions=[])
    else:
        container_state = SimpleNamespace(
            waiting=SimpleNamespace(reason=waiting_reason, message="Failed to pull image"),
            terminated=None,
            running=None
        )
        container_status = SimpleNamespace(name="app", state=container_state, ready=False)
        pod.status = SimpleNamespace(phase=phase, container_statuses=[container_status], init_container_statuses=[], conditions=[])
    return pod


def test_incident_creation_deduplication_and_recovery():
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "incidents.json"
        store = IncidentStore(json_path)
        manager = IncidentManager(store=store)

        pod_unhealthy_1 = mock_pod(waiting_reason="ErrImagePull")

        # 1. First event: DETECTED -> INC-0001 created
        inc1 = manager.process_pod_event("MODIFIED", pod_unhealthy_1)
        assert inc1 is not None
        assert inc1.incident_id == "INC-0001"
        assert inc1.status == "OPEN"
        assert inc1.occurrences == 1
        assert inc1.category == "ErrImagePull"

        # 2. Transition to ImagePullBackOff: SAME incident updated
        pod_unhealthy_2 = mock_pod(waiting_reason="ImagePullBackOff")
        inc2 = manager.process_pod_event("MODIFIED", pod_unhealthy_2)
        assert inc2 is not None
        assert inc2.incident_id == "INC-0001"
        assert inc2.status == "OPEN"
        assert inc2.occurrences == 2

        # Verify only ONE incident exists in store
        all_incidents = store.list_all()
        assert len(all_incidents) == 1

        # 3. Workload repaired: pod becomes Running + Ready
        pod_healthy = mock_pod(phase="Running", waiting_reason=None)
        manager.process_pod_event("MODIFIED", pod_healthy)

        # 4. Verify incident becomes RESOLVED
        resolved_inc = store.get_by_id("INC-0001")
        assert resolved_inc is not None
        assert resolved_inc.status == "RESOLVED"
        assert resolved_inc.resolved_at is not None
        assert "Running" in resolved_inc.state_history
