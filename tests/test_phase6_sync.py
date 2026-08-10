import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure SQLite in-memory DB is used before importing cloud modules
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SKYOPS_ENV"] = "testing"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import cloud.app.database as db_module
import cloud.app.models
from cloud.app.database import Base, get_db
from cloud.app.main import app as cloud_app

from app.agent.connector import CloudConnector
from app.agent.outbox import CloudSyncWorker, OutboxQueue
from app.incidents.manager import IncidentManager
from app.incidents.models import Incident, ResourceRef
from app.incidents.store import IncidentStore


@pytest.fixture(autouse=True)
def setup_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_module.engine = engine
    db_module.SessionLocal = TestingSessionLocal
    Base.metadata.create_all(bind=engine)

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    cloud_app.dependency_overrides[get_db] = _override_get_db
    yield
    cloud_app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def tmp_outbox(tmp_path):
    storage_path = tmp_path / "outbox.json"
    return OutboxQueue(storage_path=storage_path)


class TestCloudConnector:
    def test_redaction(self):
        connector = CloudConnector(cloud_url="http://localhost:8000", agent_token="SECRET_TOKEN_123")
        log_msg = "Error using token SECRET_TOKEN_123 at endpoint"
        redacted = connector._redact(log_msg)
        assert "SECRET_TOKEN_123" not in redacted
        assert "[REDACTED_TOKEN]" in redacted

    def test_successful_cluster_registration(self):
        client = TestClient(cloud_app)
        
        with patch("httpx.Client.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_post.return_value = mock_resp

            connector = CloudConnector(cloud_url="http://localhost:8000", agent_token="valid_token")
            success = connector.register({
                "cluster_id": "cluster-test-1",
                "kubernetes_version": "v1.28.2",
                "nodes": 3,
                "pods": 15,
                "namespaces": 4,
            })
            assert success is True

    def test_auth_failure_fails_fast(self):
        with patch("httpx.Client.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_post.return_value = mock_resp

            connector = CloudConnector(cloud_url="http://localhost:8000", agent_token="bad_token", max_retries=3)
            start_time = time.time()
            success = connector.register({"cluster_id": "c1"})
            elapsed = time.time() - start_time

            assert success is False
            # Fails fast on 401 without retrying 3 times
            assert mock_post.call_count == 1
            assert elapsed < 1.0

    def test_transient_500_retries(self):
        with patch("httpx.Client.post") as mock_post, patch("time.sleep"):
            mock_resp_500 = MagicMock()
            mock_resp_500.status_code = 500

            mock_resp_200 = MagicMock()
            mock_resp_200.status_code = 200

            mock_post.side_effect = [mock_resp_500, mock_resp_200]

            connector = CloudConnector(cloud_url="http://localhost:8000", max_retries=3, backoff_factor=0.01)
            success = connector.send_incident({"incident_id": "INC-100", "cluster_id": "c1"})
            assert success is True
            assert mock_post.call_count == 2


class TestOutboxQueue:
    def test_enqueue_and_deduplicate(self, tmp_outbox):
        payload1 = {"cluster_id": "c1", "incident_id": "INC-001", "status": "OPEN", "current_state": "ErrImagePull"}
        payload2 = {"cluster_id": "c1", "incident_id": "INC-001", "status": "OPEN", "current_state": "ImagePullBackOff"}

        id1 = tmp_outbox.enqueue(payload1)
        items = tmp_outbox.list_all()
        assert len(items) == 1
        assert items[0]["payload"]["current_state"] == "ErrImagePull"

        # Enqueue updated state for same incident
        id2 = tmp_outbox.enqueue(payload2)
        items2 = tmp_outbox.list_all()
        assert len(items2) == 1
        assert id1 == id2
        assert items2[0]["payload"]["current_state"] == "ImagePullBackOff"

    def test_outbox_retry_and_completion(self, tmp_outbox):
        payload = {"cluster_id": "c1", "incident_id": "INC-002"}
        item_id = tmp_outbox.enqueue(payload)

        # Mark failed once
        tmp_outbox.mark_failed(item_id, error="Connection timeout")
        items = tmp_outbox.list_all()
        assert items[0]["attempts"] == 1
        assert items[0]["last_error"] == "Connection timeout"

        # Mark completed
        tmp_outbox.mark_completed(item_id)
        assert len(tmp_outbox.list_all()) == 0


class TestCloudApiMultiClusterAndIdempotency:
    def test_cloud_upsert_and_idempotency(self):
        client = TestClient(cloud_app)
        client.headers["Authorization"] = "Bearer skyops-agent-secret-token"

        # Register cluster
        reg_resp = client.post("/api/v1/clusters", json={
            "cluster_id": "cluster-A",
            "name": "Cluster A",
            "kubernetes_version": "v1.28.0",
        })
        assert reg_resp.status_code in (200, 201)

        inc_payload = {
            "cluster_id": "cluster-A",
            "incident_id": "INC-LOCAL-01",
            "resource_kind": "Pod",
            "resource_namespace": "default",
            "resource_name": "broken-pod",
            "resource_uid": "uid-pod-12345",
            "category": "ImagePullFailure",
            "status": "OPEN",
            "current_state": "ErrImagePull",
            "severity": "HIGH",
            "occurrences": 1,
        }

        # First sync
        r1 = client.post("/api/v1/incidents", json=inc_payload)
        assert r1.status_code in (200, 201)

        # Second sync (duplicate retry)
        inc_payload["occurrences"] = 2
        inc_payload["current_state"] = "ImagePullBackOff"
        r2 = client.post("/api/v1/incidents", json=inc_payload)
        assert r2.status_code in (200, 201)

        # Verify only ONE cloud incident exists for cluster-A
        get_resp = client.get("/api/v1/incidents?cluster_id=cluster-A")
        assert get_resp.status_code == 200
        incidents = get_resp.json()
        assert len(incidents) == 1
        assert incidents[0]["occurrences"] == 2
        assert incidents[0]["current_state"] == "ImagePullBackOff"

    def test_multi_cluster_isolation(self):
        client = TestClient(cloud_app)
        client.headers["Authorization"] = "Bearer skyops-agent-secret-token"

        # Same resource UID in cluster-A and cluster-B
        res_uid = "same-pod-uid-999"

        inc_a = {
            "cluster_id": "cluster-A",
            "incident_id": "INC-01",
            "resource_kind": "Pod",
            "resource_namespace": "default",
            "resource_name": "app-pod",
            "resource_uid": res_uid,
            "category": "CrashLoopBackOff",
            "status": "OPEN",
            "current_state": "CrashLoopBackOff",
            "severity": "HIGH",
        }

        inc_b = {
            "cluster_id": "cluster-B",
            "incident_id": "INC-01",
            "resource_kind": "Pod",
            "resource_namespace": "default",
            "resource_name": "app-pod",
            "resource_uid": res_uid,
            "category": "ImagePullFailure",
            "status": "OPEN",
            "current_state": "ErrImagePull",
            "severity": "MEDIUM",
        }

        r_a = client.post("/api/v1/incidents", json=inc_a)
        r_b = client.post("/api/v1/incidents", json=inc_b)

        assert r_a.status_code in (200, 201)
        assert r_b.status_code in (200, 201)

        # Fetch cluster-A incidents
        resp_a = client.get("/api/v1/incidents?cluster_id=cluster-A")
        inc_list_a = resp_a.json()
        assert len(inc_list_a) == 1
        assert inc_list_a[0]["category"] == "CrashLoopBackOff"

        # Fetch cluster-B incidents
        resp_b = client.get("/api/v1/incidents?cluster_id=cluster-B")
        inc_list_b = resp_b.json()
        assert len(inc_list_b) == 1
        assert inc_list_b[0]["category"] == "ImagePullFailure"


class TestKubernetesIndependenceOnCloudFailure:
    def test_manager_operates_when_cloud_offline(self, tmp_path):
        from types import SimpleNamespace

        store = IncidentStore(tmp_path / "incidents.json")
        outbox = OutboxQueue(tmp_path / "outbox.json")
        manager = IncidentManager(store=store, outbox=outbox, cluster_id="test-cluster")

        pod_metadata = SimpleNamespace(
            name="broken-app",
            namespace="default",
            uid="pod-uid-111",
            labels={},
            annotations={},
            owner_references=[],
        )
        container_state = SimpleNamespace(
            waiting=SimpleNamespace(reason="ImagePullBackOff", message="Back-off pulling image"),
            terminated=None,
            running=None,
        )
        container_status = SimpleNamespace(
            name="app",
            state=container_state,
            last_state=SimpleNamespace(terminated=None),
            ready=False,
            restart_count=2,
            image="nginx:invalid",
        )
        pod_status = SimpleNamespace(
            phase="Pending",
            node_name="node-1",
            pod_ip="10.244.0.5",
            container_statuses=[container_status],
            init_container_statuses=[],
            ephemeral_container_statuses=[],
            conditions=[],
        )
        mock_pod = SimpleNamespace(
            metadata=pod_metadata,
            status=pod_status,
            spec=SimpleNamespace(containers=[], node_name="node-1"),
        )

        # Process pod event with Cloud completely offline/failing
        inc = manager.process_pod_event("MODIFIED", mock_pod)

        assert inc is not None
        assert inc.status == "OPEN"
        assert "ImagePullBackOff" in inc.current_state

        # Verify local store has it saved
        saved_inc = store.get_by_id(inc.incident_id)
        assert saved_inc is not None

        # Verify queued in outbox
        pending = outbox.get_pending()
        assert len(pending) == 1
        assert pending[0]["payload"]["incident_id"] == inc.incident_id
