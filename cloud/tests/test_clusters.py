def test_create_and_get_cluster(client):
    # 1. Register cluster
    payload = {
        "cluster_id": "skyops-cluster-prod-123",
        "name": "production-us-east",
        "kubernetes_version": "v1.30.2",
        "node_count": 5,
        "pod_count": 120,
        "namespace_count": 12,
    }
    resp = client.post("/api/v1/clusters", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["cluster_id"] == "skyops-cluster-prod-123"
    assert data["name"] == "production-us-east"
    assert data["status"] == "CONNECTED"
    assert data["node_count"] == 5

    # 2. Get cluster by cluster_id
    resp_get = client.get("/api/v1/clusters/skyops-cluster-prod-123")
    assert resp_get.status_code == 200
    assert resp_get.json()["cluster_id"] == "skyops-cluster-prod-123"

    # 3. List clusters
    resp_list = client.get("/api/v1/clusters")
    assert resp_list.status_code == 200
    clusters = resp_list.json()
    assert len(clusters) == 1
    assert clusters[0]["cluster_id"] == "skyops-cluster-prod-123"


def test_cluster_duplicate_registration_updates_metadata(client):
    payload_1 = {
        "cluster_id": "skyops-cluster-staging",
        "name": "staging-initial",
        "kubernetes_version": "v1.29.0",
        "node_count": 2,
    }
    client.post("/api/v1/clusters", json=payload_1)

    # Re-register with updated metrics
    payload_2 = {
        "cluster_id": "skyops-cluster-staging",
        "name": "staging-updated",
        "kubernetes_version": "v1.29.1",
        "node_count": 3,
    }
    resp_2 = client.post("/api/v1/clusters", json=payload_2)
    assert resp_2.status_code == 201
    updated_data = resp_2.json()
    assert updated_data["name"] == "staging-updated"
    assert updated_data["node_count"] == 3

    # Ensure list still contains only 1 cluster record
    resp_list = client.get("/api/v1/clusters")
    assert len(resp_list.json()) == 1


def test_get_non_existent_cluster(client):
    resp = client.get("/api/v1/clusters/does-not-exist")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_update_cluster_patch(client):
    client.post("/api/v1/clusters", json={"cluster_id": "skyops-cluster-patch"})
    
    patch_payload = {"status": "DISCONNECTED", "pod_count": 50}
    resp = client.patch("/api/v1/clusters/skyops-cluster-patch", json=patch_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "DISCONNECTED"
    assert data["pod_count"] == 50
