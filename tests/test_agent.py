import json
import urllib.request
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.agent.cluster import collect_cluster_info, get_or_create_cluster_id
from app.agent.connector import LocalDevelopmentConnector
from app.agent.health import HealthServer
from kubernetes.client.rest import ApiException


def test_agent_health_endpoints():
    health_server = HealthServer(port=18080)
    health_server.start()

    try:
        # 1. Test GET /health
        req = urllib.request.Request("http://127.0.0.1:18080/health")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "healthy"

        # 2. Test GET /ready when disconnected
        health_server.set_k8s_status(connected=False)
        req_ready = urllib.request.Request("http://127.0.0.1:18080/ready")
        with pytest.raises(urllib.error.HTTPError) as excinfo:
            urllib.request.urlopen(req_ready)
        assert excinfo.value.code == 503

        # 3. Test GET /ready when connected
        health_server.set_k8s_status(connected=True, cluster_id="skyops-cluster-test-123")
        req_ready_ok = urllib.request.Request("http://127.0.0.1:18080/ready")
        with urllib.request.urlopen(req_ready_ok) as resp_ok:
            assert resp_ok.status == 200
            data_ok = json.loads(resp_ok.read().decode("utf-8"))
            assert data_ok["status"] == "ready"
            assert data_ok["kubernetes"] == "connected"
            assert data_ok["cluster_id"] == "skyops-cluster-test-123"

    finally:
        health_server.stop()


def test_cluster_id_configmap_creation_and_persistence():
    mock_v1 = MagicMock()

    # Simulate ConfigMap 404 on first read, then successful creation
    err_404 = ApiException(status=404)
    mock_v1.read_namespaced_config_map.side_effect = err_404

    cid = get_or_create_cluster_id(v1_client=mock_v1, namespace="skyops")
    assert cid.startswith("skyops-cluster-")

    # Verify create_namespaced_config_map was called
    mock_v1.create_namespaced_config_map.assert_called_once()
    call_args = mock_v1.create_namespaced_config_map.call_args
    assert call_args[0][0] == "skyops"
    created_cm = call_args[0][1]
    assert created_cm.data["cluster_id"] == cid


def test_cluster_id_reuse_existing_configmap():
    mock_v1 = MagicMock()
    existing_cm = MagicMock()
    existing_cm.data = {"cluster_id": "skyops-cluster-existing-uuid-999"}
    mock_v1.read_namespaced_config_map.return_value = existing_cm

    cid = get_or_create_cluster_id(v1_client=mock_v1, namespace="skyops")
    assert cid == "skyops-cluster-existing-uuid-999"


def test_cluster_info_collection():
    mock_v1 = MagicMock()
    mock_api_client = MagicMock()

    # Mock version
    with patch("kubernetes.client.VersionApi") as mock_version_cls:
        mock_v_api = MagicMock()
        mock_v_api.get_code.return_value = MagicMock(git_version="v1.28.2")
        mock_version_cls.return_value = mock_v_api

        # Mock nodes
        node1 = MagicMock()
        node1.metadata.name = "node-1"
        node1.status.conditions = [MagicMock(type="Ready", status="True")]

        node2 = MagicMock()
        node2.metadata.name = "node-2"
        node2.status.conditions = [MagicMock(type="Ready", status="False")]

        mock_v1.list_node.return_value.items = [node1, node2]

        # Mock namespaces
        mock_v1.list_namespace.return_value.items = [MagicMock(), MagicMock(), MagicMock()]

        # Mock pods
        mock_v1.list_pod_for_all_namespaces.return_value.items = [MagicMock() for _ in range(15)]

        info = collect_cluster_info(
            v1_client=mock_v1,
            api_client=mock_api_client,
            cluster_id="skyops-cluster-abc",
        )

        assert info["cluster_id"] == "skyops-cluster-abc"
        assert info["kubernetes_version"] == "v1.28.2"
        assert info["nodes"] == 2
        assert info["namespaces"] == 3
        assert info["pods"] == 15
        assert info["node_names"] == ["node-1", "node-2"]
        assert info["node_readiness"] == {"node-1": "Ready", "node-2": "NotReady"}


def test_local_development_connector():
    connector = LocalDevelopmentConnector()
    c_info = {"cluster_id": "skyops-cluster-test", "nodes": 2, "kubernetes_version": "v1.28.0"}

    assert connector.register(c_info)
    assert connector.registered
    assert connector.send_incident(MagicMock(incident_id="INC-001"))


def test_rbac_manifest_security_constraints():
    manifest_dir = Path(__file__).parent.parent / "deploy"
    role_file = manifest_dir / "clusterrole.yaml"

    assert role_file.exists()
    role_docs = list(yaml.safe_load_all(role_file.read_text()))
    cluster_role = role_docs[0]

    rules = cluster_role.get("rules", [])
    
    # Verify NO secrets read access is granted
    for rule in rules:
        resources = rule.get("resources", [])
        verbs = rule.get("verbs", [])
        if "secrets" in resources:
            pytest.fail("Security Violation: ClusterRole contains 'secrets' resource!")

        # Verify read-only for workloads (pods, deployments, services, nodes)
        if any(r in resources for r in ["pods", "deployments", "services", "nodes"]):
            assert set(verbs).issubset({"get", "list", "watch"}), f"Unsafe verbs on workloads: {verbs}"
