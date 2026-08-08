import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.incidents.manager import IncidentManager
from app.incidents.store import IncidentStore


def mock_pod(
    namespace="default",
    name="skyops-broken",
    uid="uid-999",
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


def test_duplicate_modified_events_suppressed():
    """Test 1: Duplicate MODIFIED events in identical state do not increment occurrences."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = IncidentStore(Path(tmpdir) / "incidents.json")
        manager = IncidentManager(store=store)
        pod = mock_pod(waiting_reason="ErrImagePull")

        # Send same unhealthy event 10 times
        for _ in range(10):
            manager.process_pod_event("MODIFIED", pod)

        incidents = store.list_all()
        assert len(incidents) == 1
        assert incidents[0].occurrences == 1


def test_meaningful_state_transition():
    """Test 2: Transition from ErrImagePull to ImagePullBackOff triggers meaningful update."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = IncidentStore(Path(tmpdir) / "incidents.json")
        manager = IncidentManager(store=store)

        pod1 = mock_pod(waiting_reason="ErrImagePull")
        inc1 = manager.process_pod_event("MODIFIED", pod1)
        assert inc1.occurrences == 1

        pod2 = mock_pod(waiting_reason="ImagePullBackOff", waiting_msg="Back-off pulling image")
        inc2 = manager.process_pod_event("MODIFIED", pod2)
        assert inc2.incident_id == inc1.incident_id
        assert inc2.occurrences == 2
        assert "ImagePullBackOff" in inc2.state_history


def test_duplicate_state_transition_suppression():
    """Test 3: Multiple ImagePullBackOff events after transition are ignored."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = IncidentStore(Path(tmpdir) / "incidents.json")
        manager = IncidentManager(store=store)

        pod1 = mock_pod(waiting_reason="ErrImagePull")
        manager.process_pod_event("MODIFIED", pod1)

        pod2 = mock_pod(waiting_reason="ImagePullBackOff")
        manager.process_pod_event("MODIFIED", pod2)

        # Send ImagePullBackOff 5 more times
        for _ in range(5):
            manager.process_pod_event("MODIFIED", pod2)

        incidents = store.list_all()
        assert len(incidents) == 1
        assert incidents[0].occurrences == 2
        assert incidents[0].state_history == ["ErrImagePull", "ImagePullBackOff"]


def test_recovery_idempotency():
    """Test 4 & 5: Pod becomes Running+Ready -> RESOLVED once; duplicate recovery events do nothing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = IncidentStore(Path(tmpdir) / "incidents.json")
        manager = IncidentManager(store=store)

        pod_unhealthy = mock_pod(waiting_reason="ImagePullBackOff")
        manager.process_pod_event("MODIFIED", pod_unhealthy)

        pod_healthy = mock_pod(phase="Running", waiting_reason=None)

        # First healthy event resolves incident
        manager.process_pod_event("MODIFIED", pod_healthy)

        resolved_inc = store.get_by_id("INC-0001")
        assert resolved_inc.status == "RESOLVED"
        assert resolved_inc.resolved_at is not None

        # Subsequent healthy events do not crash or create/update incidents
        for _ in range(5):
            manager.process_pod_event("MODIFIED", pod_healthy)

        all_incidents = store.list_all()
        assert len(all_incidents) == 1
        assert all_incidents[0].status == "RESOLVED"


def test_ai_trigger_deduplication():
    """Test 6: AI analyzer is called only on initial creation and meaningful state transitions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = IncidentStore(Path(tmpdir) / "incidents.json")
        mock_ai = MagicMock()
        manager = IncidentManager(store=store, ai_analyzer=mock_ai)

        pod1 = mock_pod(waiting_reason="ErrImagePull")

        # 10 identical events
        for _ in range(10):
            manager.process_pod_event("MODIFIED", pod1)

        # AI analyzer should be called exactly ONCE
        assert mock_ai.analyze_incident.call_count == 1

        # Meaningful state transition
        pod2 = mock_pod(waiting_reason="ImagePullBackOff")
        manager.process_pod_event("MODIFIED", pod2)

        # AI analyzer should now be called twice
        assert mock_ai.analyze_incident.call_count == 2

        # 5 identical MODIFIED events for ImagePullBackOff
        for _ in range(5):
            manager.process_pod_event("MODIFIED", pod2)

        # AI analyzer call count should remain 2
        assert mock_ai.analyze_incident.call_count == 2
