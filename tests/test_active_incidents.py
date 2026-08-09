import concurrent.futures
import tempfile
from pathlib import Path
from types import SimpleNamespace

from app.incidents.manager import IncidentManager
from app.incidents.models import Incident, ResourceRef
from app.incidents.store import IncidentStore


def mock_pod(
    namespace="default",
    name="skyops-dedup-test",
    uid="uid-111",
    phase="Pending",
    waiting_reason="ErrImagePull",
    waiting_msg="Failed to pull image",
):
    pod = SimpleNamespace()
    pod.metadata = SimpleNamespace(namespace=namespace, name=name, uid=uid)
    if phase == "Running" and not waiting_reason:
        container_state = SimpleNamespace(waiting=None, terminated=None, running=SimpleNamespace())
        container_status = SimpleNamespace(name="app", state=container_state, ready=True)
        pod.status = SimpleNamespace(
            phase="Running",
            container_statuses=[container_status],
            init_container_statuses=[],
            conditions=[],
        )
    else:
        container_state = SimpleNamespace(
            waiting=SimpleNamespace(reason=waiting_reason, message=waiting_msg),
            terminated=None,
            running=None,
        )
        container_status = SimpleNamespace(name="app", state=container_state, ready=False)
        pod.status = SimpleNamespace(
            phase=phase,
            container_statuses=[container_status],
            init_container_statuses=[],
            conditions=[],
        )
    return pod


def test_1_same_resource_cannot_create_two_active_incidents():
    """Requirement 1: Same Kubernetes resource cannot create two active incidents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = IncidentStore(Path(tmpdir) / "incidents.json")
        manager = IncidentManager(store=store)

        pod_pending = mock_pod(phase="Pending", waiting_reason="PodPending", uid="uid-active-1")
        inc1 = manager.process_pod_event("MODIFIED", pod_pending)

        pod_err = mock_pod(phase="Pending", waiting_reason="ErrImagePull", uid="uid-active-1")
        inc2 = manager.process_pod_event("MODIFIED", pod_err)

        open_incidents = [i for i in store.list_all() if i.status == "OPEN"]
        assert len(open_incidents) == 1
        assert inc1.incident_id == inc2.incident_id == "INC-0001"
        assert open_incidents[0].category == "ErrImagePull"


def test_2_rapid_duplicate_events():
    """Requirement 2: Rapid duplicate events map to a single active incident."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = IncidentStore(Path(tmpdir) / "incidents.json")
        manager = IncidentManager(store=store)

        pod = mock_pod(waiting_reason="ErrImagePull", uid="uid-rapid-1")
        for _ in range(15):
            manager.process_pod_event("MODIFIED", pod)

        open_incidents = [i for i in store.list_all() if i.status == "OPEN"]
        assert len(open_incidents) == 1
        assert open_incidents[0].occurrences == 1


def test_3_concurrent_processing():
    """Requirement 3: Concurrent processing of events for the same resource is thread-safe."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = IncidentStore(Path(tmpdir) / "incidents.json")
        manager = IncidentManager(store=store)
        pod = mock_pod(waiting_reason="ErrImagePull", uid="uid-concurrent-1")

        def process_event():
            return manager.process_pod_event("MODIFIED", pod)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_event) for _ in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        open_incidents = [i for i in store.list_all() if i.status == "OPEN"]
        assert len(open_incidents) == 1
        assert open_incidents[0].incident_id == "INC-0001"


def test_4_state_transition():
    """Requirement 4: State transition updates the existing active incident."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = IncidentStore(Path(tmpdir) / "incidents.json")
        manager = IncidentManager(store=store)

        pod_err = mock_pod(waiting_reason="ErrImagePull", uid="uid-trans-1")
        inc1 = manager.process_pod_event("MODIFIED", pod_err)

        pod_backoff = mock_pod(waiting_reason="ImagePullBackOff", uid="uid-trans-1")
        inc2 = manager.process_pod_event("MODIFIED", pod_backoff)

        assert inc1.incident_id == inc2.incident_id == "INC-0001"
        assert inc2.occurrences == 2
        assert "ImagePullBackOff" in inc2.state_history


def test_5_recovery():
    """Requirement 5: Workload recovery resolves the active incident."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = IncidentStore(Path(tmpdir) / "incidents.json")
        manager = IncidentManager(store=store)

        pod_unhealthy = mock_pod(waiting_reason="ImagePullBackOff", uid="uid-rec-1")
        manager.process_pod_event("MODIFIED", pod_unhealthy)

        pod_healthy = mock_pod(phase="Running", waiting_reason=None, uid="uid-rec-1")
        manager.process_pod_event("MODIFIED", pod_healthy)

        resolved_inc = store.get_by_id("INC-0001")
        assert resolved_inc.status == "RESOLVED"
        assert resolved_inc.resolved_at is not None

        open_incidents = [i for i in store.list_all() if i.status == "OPEN"]
        assert len(open_incidents) == 0


def test_6_new_kubernetes_uid():
    """Requirement 6: Recreated Pod with new UID creates a distinct incident identity."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = IncidentStore(Path(tmpdir) / "incidents.json")
        manager = IncidentManager(store=store)

        # First pod instance with UID 111
        pod1 = mock_pod(name="skyops-dedup-test", uid="uid-111", waiting_reason="ErrImagePull")
        inc1 = manager.process_pod_event("MODIFIED", pod1)
        assert inc1.incident_id == "INC-0001"

        # Recover pod1
        pod1_healthy = mock_pod(name="skyops-dedup-test", uid="uid-111", phase="Running", waiting_reason=None)
        manager.process_pod_event("MODIFIED", pod1_healthy)
        assert store.get_by_id("INC-0001").status == "RESOLVED"

        # New pod instance created with same name but new UID 222
        pod2 = mock_pod(name="skyops-dedup-test", uid="uid-222", waiting_reason="ErrImagePull")
        inc2 = manager.process_pod_event("MODIFIED", pod2)

        assert inc2.incident_id == "INC-0002"
        assert inc2.resource.uid == "uid-222"
        assert store.get_by_id("INC-0001").status == "RESOLVED"
        assert store.get_by_id("INC-0002").status == "OPEN"


def test_store_invariant_at_most_one_open_incident():
    """IncidentStore invariant: identity_key and resource UID map to at most ONE open incident."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = IncidentStore(Path(tmpdir) / "incidents.json")
        res = ResourceRef(kind="Pod", name="skyops-pod", namespace="default", uid="uid-inv-1")

        inc1 = Incident(
            incident_id="INC-0001",
            status="OPEN",
            resource=res,
            category="ImagePullFailure",
            current_state="ErrImagePull",
            identity_key="default:Pod:uid-inv-1:ImagePullFailure",
        )
        store.save(inc1)

        # Attempt to save a SECOND open incident with a different ID for the same resource
        inc2 = Incident(
            incident_id="INC-0002",
            status="OPEN",
            resource=res,
            category="ImagePullFailure",
            current_state="ImagePullBackOff",
            identity_key="default:Pod:uid-inv-1:ImagePullFailure",
        )
        store.save(inc2)

        open_incidents = [i for i in store.list_all() if i.status == "OPEN"]
        assert len(open_incidents) == 1
        assert open_incidents[0].incident_id == "INC-0001"


def test_critical_persistence_one_open_incident_across_reloads():
    """Critical Persistence Test: Enforce one open incident invariant across repeated saves and store reloads."""
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "incidents.json"
        store = IncidentStore(json_path)
        manager = IncidentManager(store=store)

        pod = mock_pod(waiting_reason="ImagePullBackOff", uid="uid-abc123")

        for i in range(10):
            inc = manager.process_pod_event("MODIFIED", pod)
            open_for_uid = [item for item in store.list_all() if item.status == "OPEN" and item.resource.uid == "uid-abc123"]
            assert len(open_for_uid) == 1, f"Iteration {i}: Expected 1 open incident, found {len(open_for_uid)}"
            assert open_for_uid[0].incident_id == "INC-0001"

        # Reload store from disk
        reloaded_store = IncidentStore(json_path)
        reloaded_open = [item for item in reloaded_store.list_all() if item.status == "OPEN" and item.resource.uid == "uid-abc123"]
        assert len(reloaded_open) == 1
        assert reloaded_open[0].incident_id == "INC-0001"


def test_restart_manager_and_reload_store():
    """Restart Test: Destroy IncidentManager / reload Store and re-process identical event."""
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "incidents.json"

        # Session 1
        store1 = IncidentStore(json_path)
        manager1 = IncidentManager(store=store1)
        pod = mock_pod(waiting_reason="ImagePullBackOff", uid="uid-restart-1")

        inc1 = manager1.process_pod_event("MODIFIED", pod)
        assert inc1.incident_id == "INC-0001"
        assert inc1.occurrences == 1

        # Simulate restart by destroying manager and reloading store from disk
        del manager1
        del store1

        store2 = IncidentStore(json_path)
        manager2 = IncidentManager(store=store2)

        # Process identical event
        inc2 = manager2.process_pod_event("ADDED", pod)
        assert inc2.incident_id == "INC-0001"
        assert inc2.occurrences == 1

        all_incidents = store2.list_all()
        assert len(all_incidents) == 1
        assert all_incidents[0].incident_id == "INC-0001"
        assert all_incidents[0].status == "OPEN"


def test_live_watch_startup_replay():
    """Live Watch Startup Test: Replaying existing pods on watch reconnect does not duplicate incidents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "incidents.json"
        store = IncidentStore(json_path)
        manager = IncidentManager(store=store)

        pod = mock_pod(name="skyops-dedup-test", uid="uid-replay-1", waiting_reason="ImagePullBackOff")

        # Initial event
        inc = manager.process_pod_event("ADDED", pod)
        assert inc.incident_id == "INC-0001"
        assert inc.occurrences == 1

        # Simulate watcher reconnect sending initial list of existing pods (ADDED)
        for _ in range(5):
            replayed_inc = manager.process_pod_event("ADDED", pod)
            assert replayed_inc.incident_id == "INC-0001"
            assert replayed_inc.occurrences == 1

        open_incidents = [item for item in store.list_all() if item.status == "OPEN"]
        assert len(open_incidents) == 1
        assert open_incidents[0].incident_id == "INC-0001"
        assert open_incidents[0].occurrences == 1

