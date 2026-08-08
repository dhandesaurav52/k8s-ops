from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

from app.incidents.manager import IncidentManager
from app.incidents.store import IncidentStore
from app.ai.analyzer import AIAnalyzer
from app.ai.provider import AIProvider
from app.ai.models import AIAnalysisResponse


class DummyMockAIProvider(AIProvider):
    def __init__(self):
        self.call_count = 0

    @property
    def name(self) -> str:
        return "mock_ai"

    def is_available(self) -> bool:
        return True

    def analyze(self, evidence, incident_id=""):
        self.call_count += 1
        return AIAnalysisResponse(
            provider="mock_ai",
            model="mock-v1",
            generated_at="2026-08-08T00:00:00Z",
            analysis_version=1,
            status="SUCCESS",
            result={
                "summary": "Mock AI reasoning confirms image pull failure.",
                "incident_type": "ImagePullFailure",
                "severity": "MEDIUM",
                "root_cause": {
                    "statement": "The referenced container image tag does not exist.",
                    "confidence": 0.95
                },
                "evidence": [
                    {"statement": "Pod in ErrImagePull state", "source": "pod.status"}
                ],
                "impact": {"level": "MEDIUM", "statement": "Pod is unusable."},
                "recommendations": [{"priority": "HIGH", "action": "Fix deployment image tag."}],
                "confirmed_facts": ["ErrImagePull state detected"],
                "likely_causes": ["Image name typo"],
                "unknowns": ["Registry credentials status"],
                "next_checks": ["Inspect registry repo"]
            },
            usage={
                "provider": "mock_ai",
                "model": "mock-v1",
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
                "request_duration_ms": 12.0,
                "estimated_cost_usd": 0.00003,
                "incident_id": incident_id
            }
        )


def create_unhealthy_mock_pod(name="ai-test-pod", namespace="default"):
    pod = SimpleNamespace()
    pod.metadata = SimpleNamespace(
        name=name,
        namespace=namespace,
        uid=f"uid-{name}",
        creation_timestamp="2026-08-08T00:00:00Z",
        labels={"app": "test-ai"},
        annotations={},
        owner_references=[]
    )
    c_state = SimpleNamespace(
        running=None,
        waiting=SimpleNamespace(reason="ErrImagePull", message="Cannot pull image foo:bar"),
        terminated=None
    )
    c_status = SimpleNamespace(
        name="main",
        image="foo:bar",
        image_id="",
        ready=False,
        restart_count=0,
        state=c_state
    )
    pod.spec = SimpleNamespace(
        node_name="node-1",
        containers=[SimpleNamespace(name="main", image="foo:bar", env=[], env_from=[])],
        init_containers=[],
        volumes=[]
    )
    pod.status = SimpleNamespace(
        phase="Pending",
        pod_ip="10.244.0.50",
        host_ip="192.168.1.1",
        node_name="node-1",
        start_time="2026-08-08T00:00:00Z",
        container_statuses=[c_status],
        init_container_statuses=[],
        conditions=[]
    )
    return pod


def test_full_ai_incident_integration(tmp_path):
    store_file = tmp_path / "incidents.json"
    store = IncidentStore(file_path=store_file)

    mock_provider = DummyMockAIProvider()
    ai_analyzer = AIAnalyzer(provider=mock_provider)

    manager = IncidentManager(
        store=store,
        k8s_client=None,
        investigation_engine=None,  # standard engine with null APIs
        ai_analyzer=ai_analyzer,
    )

    pod = create_unhealthy_mock_pod()

    # Process Pod Event -> Incident DETECTED -> Deep Investigation -> AI Analysis -> Stored
    incident = manager.process_pod_event("ADDED", pod)

    assert incident is not None
    assert incident.status == "OPEN"
    assert incident.category in ("ErrImagePull", "ImagePullFailure")
    assert incident.ai_status == "SUCCESS"
    assert incident.ai_analysis is not None
    assert incident.ai_analysis["result"]["summary"] == "Mock AI reasoning confirms image pull failure."
    assert incident.ai_analysis["result"]["root_cause"]["confidence"] == 0.95

    # Deterministic diagnosis is also present
    assert incident.diagnosis["incident_category"] == "ImagePullFailure"

    # Verify saved in IncidentStore
    loaded = store.get_by_id(incident.incident_id)
    assert loaded is not None
    assert loaded.ai_status == "SUCCESS"
    assert loaded.ai_analysis["result"]["root_cause"]["confidence"] == 0.95
    assert mock_provider.call_count == 1
