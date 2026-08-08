import pytest
from kubernetes import client
from app.kubernetes.client import check_connection, get_k8s_clients
from app.investigation.collectors.pod import PodCollector
from app.investigation.collectors.replicaset import ReplicaSetCollector
from app.investigation.collectors.deployment import DeploymentCollector
from app.investigation.collectors.node import NodeCollector
from app.investigation.collectors.storage import StorageCollector


def test_python_k8s_client_real_models_compatibility():
    """
    Validates that collectors can inspect actual Python kubernetes.client V1 model objects.
    This ensures no AttributeError occurs when inspecting real Kubernetes API responses.
    """
    # 1. Real V1Pod object
    v1_pod = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name="real-k8s-pod",
            namespace="default",
            uid="uid-real-pod-999",
            labels={"app": "real-app"},
            owner_references=[
                client.V1OwnerReference(
                    api_version="apps/v1",
                    kind="ReplicaSet",
                    name="real-app-rs-001",
                    uid="uid-rs-001",
                    controller=True
                )
            ]
        ),
        spec=client.V1PodSpec(
            node_name="real-node-1",
            containers=[
                client.V1Container(
                    name="real-container",
                    image="nginx:invalid-tag-for-test",
                    env=[
                        client.V1EnvVar(
                            name="SECRET_TOKEN",
                            value_from=client.V1EnvVarSource(
                                secret_key_ref=client.V1SecretKeySelector(
                                    name="real-app-secret",
                                    key="token"
                                )
                            )
                        )
                    ]
                )
            ],
            volumes=[
                client.V1Volume(
                    name="real-pv-vol",
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name="real-pvc"
                    )
                )
            ]
        ),
        status=client.V1PodStatus(
            phase="Pending",
            pod_ip="10.244.0.88",
            host_ip="192.168.1.50",
            container_statuses=[
                client.V1ContainerStatus(
                    name="real-container",
                    image="nginx:invalid-tag-for-test",
                    image_id="",
                    ready=False,
                    restart_count=2,
                    state=client.V1ContainerState(
                        waiting=client.V1ContainerStateWaiting(
                            reason="ImagePullBackOff",
                            message="Back-off pulling image nginx:invalid-tag-for-test"
                        )
                    )
                )
            ]
        )
    )

    pod_info, configmaps_ref, secrets_ref, findings = PodCollector.collect(
        v1_api=None, namespace="default", pod_name="real-k8s-pod", pod_obj=v1_pod
    )

    assert pod_info["name"] == "real-k8s-pod"
    assert pod_info["phase"] == "Pending"
    assert pod_info["pod_ip"] == "10.244.0.88"
    assert pod_info["node_name"] == "real-node-1"
    assert len(pod_info["containers"]) == 1
    assert pod_info["containers"][0]["state"] == "waiting"
    assert pod_info["containers"][0]["state_detail"]["reason"] == "ImagePullBackOff"

    # Secret reference metadata collected safely
    assert len(secrets_ref) == 1
    assert secrets_ref[0]["name"] == "real-app-secret"

    # Volume reference collected
    assert len(pod_info["volumes"]) == 1
    assert pod_info["volumes"][0]["claim_name"] == "real-pvc"


def test_real_cluster_connectivity_check():
    """
    Attempts to check if a real cluster is present. If present, verifies connectivity;
    if not, skips gracefully without failing test suite.
    """
    try:
        v1, api_client = get_k8s_clients()
        connected = check_connection(v1)
        if not connected:
            pytest.skip("No real Kubernetes cluster reachable in test environment")
    except Exception:
        pytest.skip("No kubeconfig or cluster access in current environment")
