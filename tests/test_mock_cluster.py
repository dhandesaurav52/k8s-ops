import tempfile
from pathlib import Path
from types import SimpleNamespace

from app.incidents.manager import IncidentManager
from app.incidents.store import IncidentStore


def build_mock_pod(name: str, namespace: str = "default", phase: str = "Running", reason: str = None, uid: str = None):
    pod = SimpleNamespace()
    pod.metadata = SimpleNamespace(
        name=name,
        namespace=namespace,
        uid=uid or f"uid-{name}",
    )
    if phase == "Running" and not reason:
        c_state = SimpleNamespace(waiting=None, terminated=None, running=SimpleNamespace())
        c_status = SimpleNamespace(name="main", state=c_state, ready=True)
        pod.status = SimpleNamespace(phase="Running", container_statuses=[c_status], init_container_statuses=[], conditions=[])
    else:
        c_state = SimpleNamespace(
            waiting=SimpleNamespace(reason=reason, message=f"Container failed with {reason}"),
            terminated=None,
            running=None,
        )
        c_status = SimpleNamespace(name="main", state=c_state, ready=False)
        pod.status = SimpleNamespace(phase=phase, container_statuses=[c_status], init_container_statuses=[], conditions=[])
    return pod


def test_full_cluster_simulation():
    with tempfile.TemporaryDirectory() as tmpdir:
        json_file = Path(tmpdir) / "incidents.json"
        store = IncidentStore(json_file)
        manager = IncidentManager(store=store)

        # -------------------------------------------------------------
        # STEP 1: Healthy Pod (nginx) -> Should NOT create an incident
        # -------------------------------------------------------------
        healthy_pod = build_mock_pod("nginx", phase="Running", reason=None)
        res1 = manager.process_pod_event("ADDED", healthy_pod)
        assert res1 is None
        assert len(store.list_all()) == 0

        # -------------------------------------------------------------
        # STEP 2: Broken Pod (broken-nginx) -> Creates ONE incident
        # -------------------------------------------------------------
        broken_pod_1 = build_mock_pod("broken-nginx", phase="Pending", reason="ErrImagePull")
        inc1 = manager.process_pod_event("ADDED", broken_pod_1)
        assert inc1 is not None
        assert inc1.incident_id == "INC-0001"
        assert inc1.status == "OPEN"
        assert len(store.list_all()) == 1

        # -------------------------------------------------------------
        # STEP 3: Repeated events (ErrImagePull -> ImagePullBackOff)
        # -------------------------------------------------------------
        broken_pod_2 = build_mock_pod("broken-nginx", phase="Pending", reason="ImagePullBackOff")
        inc1_updated = manager.process_pod_event("MODIFIED", broken_pod_2)

        # MUST be the SAME incident
        assert inc1_updated.incident_id == "INC-0001"
        assert inc1_updated.occurrences == 2
        assert len(store.list_all()) == 1, "Repeated events must NOT create duplicate incidents"

        # -------------------------------------------------------------
        # STEP 4: Fix broken workload -> Incident becomes RESOLVED
        # -------------------------------------------------------------
        fixed_pod = build_mock_pod("broken-nginx", phase="Running", reason=None)
        manager.process_pod_event("MODIFIED", fixed_pod)

        stored_inc = store.get_by_id("INC-0001")
        assert stored_inc.status == "RESOLVED"
        assert stored_inc.resolved_at is not None

        # -------------------------------------------------------------
        # STEP 5: Different broken workload -> Creates SECOND incident
        # -------------------------------------------------------------
        broken_redis = build_mock_pod("broken-redis", phase="Pending", reason="CrashLoopBackOff")
        inc2 = manager.process_pod_event("ADDED", broken_redis)
        assert inc2 is not None
        assert inc2.incident_id == "INC-0002"
        assert len(store.list_all()) == 2
