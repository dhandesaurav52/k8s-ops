def test_create_and_get_incident(client):
    payload = {
        "cluster_id": "skyops-cluster-a",
        "incident_id": "INC-0001",
        "resource": {
            "kind": "Pod",
            "namespace": "default",
            "name": "nginx-broken-pod",
            "uid": "uid-12345",
        },
        "category": "ImagePullFailure",
        "status": "OPEN",
        "current_state": "ImagePullBackOff",
        "severity": "HIGH",
        "occurrences": 1,
        "diagnosis": {"root_cause": "Image not found on registry"},
        "investigation": {"events": ["BackOff 5m"]},
        "ai_analysis": {"summary": "Check image tag and pull secret"},
    }

    resp = client.post("/api/v1/incidents", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["cluster_id"] == "skyops-cluster-a"
    assert data["incident_id"] == "INC-0001"
    assert data["resource_name"] == "nginx-broken-pod"
    assert data["severity"] == "HIGH"
    assert data["diagnosis"]["root_cause"] == "Image not found on registry"

    db_id = data["id"]

    # Retrieve by DB ID
    resp_get = client.get(f"/api/v1/incidents/{db_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["incident_id"] == "INC-0001"

    # Retrieve by incident_id + cluster_id query
    resp_get_key = client.get("/api/v1/incidents/INC-0001?cluster_id=skyops-cluster-a")
    assert resp_get_key.status_code == 200
    assert resp_get_key.json()["id"] == db_id


def test_incident_deduplication_on_same_cluster(client):
    # Cluster A + INC-0001
    payload_1 = {
        "cluster_id": "skyops-cluster-a",
        "incident_id": "INC-0001",
        "resource_name": "app-pod",
        "category": "CrashLoopBackOff",
        "severity": "MEDIUM",
        "occurrences": 1,
    }
    client.post("/api/v1/incidents", json=payload_1)

    # Post again with higher occurrences
    payload_2 = {
        "cluster_id": "skyops-cluster-a",
        "incident_id": "INC-0001",
        "resource_name": "app-pod",
        "category": "CrashLoopBackOff",
        "severity": "HIGH",
        "occurrences": 5,
    }
    resp_2 = client.post("/api/v1/incidents", json=payload_2)
    assert resp_2.status_code == 201
    data_2 = resp_2.json()
    assert data_2["occurrences"] == 5
    assert data_2["severity"] == "HIGH"

    # Verify database list has only 1 incident total for Cluster A
    resp_list = client.get("/api/v1/incidents?cluster_id=skyops-cluster-a")
    assert len(resp_list.json()) == 1


def test_multi_cluster_isolation_same_incident_id(client):
    # Cluster A + INC-0001
    p1 = {
        "cluster_id": "skyops-cluster-a",
        "incident_id": "INC-0001",
        "resource_name": "pod-cluster-a",
        "category": "OOMKilled",
    }
    client.post("/api/v1/incidents", json=p1)

    # Cluster B + INC-0001
    p2 = {
        "cluster_id": "skyops-cluster-b",
        "incident_id": "INC-0001",
        "resource_name": "pod-cluster-b",
        "category": "CrashLoopBackOff",
    }
    client.post("/api/v1/incidents", json=p2)

    # Verify both incidents exist independently
    resp_all = client.get("/api/v1/incidents")
    assert len(resp_all.json()) == 2

    resp_a = client.get("/api/v1/incidents?cluster_id=skyops-cluster-a")
    assert len(resp_a.json()) == 1
    assert resp_a.json()[0]["resource_name"] == "pod-cluster-a"

    resp_b = client.get("/api/v1/incidents?cluster_id=skyops-cluster-b")
    assert len(resp_b.json()) == 1
    assert resp_b.json()[0]["resource_name"] == "pod-cluster-b"


def test_update_and_resolve_incident(client):
    p = {
        "cluster_id": "skyops-cluster-c",
        "incident_id": "INC-9999",
        "resource_name": "worker-pod",
        "category": "DiskFull",
    }
    create_resp = client.post("/api/v1/incidents", json=p)
    inc_id = create_resp.json()["id"]

    # Resolve incident via endpoint
    res_resp = client.post(f"/api/v1/incidents/{inc_id}/resolve")
    assert res_resp.status_code == 200
    res_data = res_resp.json()
    assert res_data["status"] == "RESOLVED"
    assert res_data["resolved_at"] is not None


def test_incident_invalid_payload_validation(client):
    # Invalid severity
    bad_severity = {
        "cluster_id": "cluster-x",
        "incident_id": "INC-001",
        "resource_name": "pod-1",
        "category": "Error",
        "severity": "SUPER_CRITICAL",
    }
    resp_1 = client.post("/api/v1/incidents", json=bad_severity)
    assert resp_1.status_code == 422

    # Missing required category
    missing_cat = {
        "cluster_id": "cluster-x",
        "incident_id": "INC-001",
        "resource_name": "pod-1",
    }
    resp_2 = client.post("/api/v1/incidents", json=missing_cat)
    assert resp_2.status_code == 422


def test_create_incident_with_null_json_fields_and_long_state(client):
    # Agent payload without AI key (ai_analysis: None, diagnosis: None, long current_state)
    payload = {
        "cluster_id": "skyops-cluster-prod",
        "incident_id": "INC-8888",
        "resource": {
            "kind": "Pod",
            "namespace": "production",
            "name": "large-log-pod-0",
            "uid": "uid-log-pod-8888",
        },
        "category": "CrashLoopBackOff",
        "status": "OPEN",
        "current_state": "A" * 500,  # Long state message > 100 chars
        "severity": "HIGH",
        "occurrences": 1,
        "diagnosis": None,
        "investigation": None,
        "ai_analysis": None,
        "state_history": None,
    }

    resp = client.post("/api/v1/incidents", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["cluster_id"] == "skyops-cluster-prod"
    assert data["incident_id"] == "INC-8888"
    assert data["diagnosis"] == {}
    assert data["investigation"] == {}
    assert data["ai_analysis"] == {}
    assert data["state_history"] == []
    assert len(data["current_state"]) == 500

