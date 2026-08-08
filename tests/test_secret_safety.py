import pytest
import json
from types import SimpleNamespace
from app.incidents.models import Incident, ResourceRef
from app.investigation.engine import InvestigationEngine
from app.investigation.collectors.pod import PodCollector


def test_secret_safety_no_secret_values_in_investigation():
    # Construct a pod that references a secret both via volume and via envVar
    secret_volume = SimpleNamespace(
        name="db-secret-vol",
        persistent_volume_claim=None,
        config_map=None,
        secret=SimpleNamespace(secret_name="db-credentials-secret"),
        host_path=None,
        empty_dir=None
    )
    
    secret_env_var = SimpleNamespace(
        name="DB_PASSWORD",
        value_from=SimpleNamespace(
            secret_key_ref=SimpleNamespace(name="db-credentials-secret", key="password"),
            config_map_key_ref=None
        )
    )

    pod = SimpleNamespace()
    pod.metadata = SimpleNamespace(
        name="secure-app-pod",
        namespace="prod",
        uid="uid-secure-app",
        creation_timestamp="2026-08-08T00:00:00Z",
        labels={"app": "secure-app"},
        annotations={},
        owner_references=[]
    )
    c_state = SimpleNamespace(
        running=None,
        waiting=SimpleNamespace(reason="CrashLoopBackOff", message="Database auth failed"),
        terminated=None
    )
    c_status = SimpleNamespace(
        name="app-container",
        image="my-app:v1",
        image_id="",
        ready=False,
        restart_count=5,
        state=c_state
    )
    pod.spec = SimpleNamespace(
        node_name="node-secure",
        containers=[SimpleNamespace(name="app-container", image="my-app:v1", env=[secret_env_var], env_from=[])],
        init_containers=[],
        volumes=[secret_volume]
    )
    pod.status = SimpleNamespace(
        phase="Running",
        pod_ip="10.244.2.50",
        host_ip="192.168.1.101",
        node_name="node-secure",
        start_time="2026-08-08T00:00:00Z",
        container_statuses=[c_status],
        init_container_statuses=[],
        conditions=[]
    )

    incident = Incident(
        incident_id="INC-SEC-1",
        status="OPEN",
        resource=ResourceRef(kind="Pod", name="secure-app-pod", namespace="prod", uid="uid-secure-app"),
        category="CrashLoop",
        current_state="CrashLoopBackOff",
    )

    engine = InvestigationEngine(v1_api=None, apps_v1_api=None, storage_v1_api=None)
    result = engine.investigate(incident, pod_obj=pod)

    res_dict = result.to_dict()
    res_str = json.dumps(res_dict)

    # Assert secret metadata IS collected
    assert len(res_dict["secrets"]) == 1
    assert res_dict["secrets"][0]["name"] == "db-credentials-secret"
    assert res_dict["secrets"][0]["namespace"] == "prod"

    # Assert NO secret values / data keys exist
    assert "data" not in res_dict["secrets"][0]
    assert "stringData" not in res_dict["secrets"][0]
    assert "value" not in res_dict["secrets"][0]
    assert "supersecretpassword" not in res_str
