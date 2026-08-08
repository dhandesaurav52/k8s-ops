import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace
from app.investigation.collectors.service import ServiceCollector


def test_discover_all_services_targeting_pod():
    pod_labels = {"app": "payment-api", "environment": "production"}

    # Mock 3 Services in same namespace
    # Service A matches app=payment-api
    svcA = SimpleNamespace()
    svcA.metadata = SimpleNamespace(name="payment-service-public", uid="uid-svcA")
    svcA.spec = SimpleNamespace(
        type="ClusterIP",
        cluster_ip="10.96.0.10",
        selector={"app": "payment-api"},
        ports=[SimpleNamespace(name="http", port=80, protocol="TCP", target_port=8080)],
        session_affinity="None"
    )

    # Service B matches app=payment-api and environment=production
    svcB = SimpleNamespace()
    svcB.metadata = SimpleNamespace(name="payment-service-internal", uid="uid-svcB")
    svcB.spec = SimpleNamespace(
        type="ClusterIP",
        cluster_ip="10.96.0.11",
        selector={"app": "payment-api", "environment": "production"},
        ports=[SimpleNamespace(name="metrics", port=9090, protocol="TCP", target_port=9090)],
        session_affinity="None"
    )

    # Service C does NOT match (app=other-api)
    svcC = SimpleNamespace()
    svcC.metadata = SimpleNamespace(name="unrelated-service", uid="uid-svcC")
    svcC.spec = SimpleNamespace(
        type="ClusterIP",
        cluster_ip="10.96.0.12",
        selector={"app": "other-api"},
        ports=[SimpleNamespace(name="http", port=80, protocol="TCP", target_port=80)],
        session_affinity="None"
    )

    mock_v1 = MagicMock()
    mock_v1.list_namespaced_service.return_value = SimpleNamespace(items=[svcA, svcB, svcC])

    services, rels, findings = ServiceCollector.collect(
        v1_api=mock_v1,
        namespace="default",
        pod_name="payment-api-pod-123",
        pod_labels=pod_labels
    )

    # Asserts BOTH matching services are discovered!
    assert len(services) == 2
    svc_names = [s["name"] for s in services]
    assert "payment-service-public" in svc_names
    assert "payment-service-internal" in svc_names
    assert "unrelated-service" not in svc_names

    # Asserts relationships generated for both services
    assert len(rels) == 2
    rel_sources = [r["from"] for r in rels]
    assert "Service/default/payment-service-public" in rel_sources
    assert "Service/default/payment-service-internal" in rel_sources
