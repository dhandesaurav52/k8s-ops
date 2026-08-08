import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("SkyOps.PodCollector")


class PodCollector:
    """
    Collects detailed state, container information, volume references,
    and configmap/secret references for a Kubernetes Pod.
    """

    @staticmethod
    def collect(
        v1_api: Any,
        namespace: str,
        pod_name: str,
        pod_obj: Optional[Any] = None
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Returns: (pod_info, configmaps_ref, secrets_ref, findings)
        """
        if not pod_obj and v1_api:
            try:
                pod_obj = v1_api.read_namespaced_pod(name=pod_name, namespace=namespace)
            except Exception as e:
                logger.error(f"Error fetching pod {namespace}/{pod_name}: {e}")
                return {}, [], [], [{
                    "severity": "CRITICAL",
                    "category": "POD",
                    "message": f"Failed to retrieve pod {namespace}/{pod_name}: {e}",
                    "evidence": [str(e)]
                }]

        if not pod_obj:
            return {}, [], [], []

        meta = getattr(pod_obj, "metadata", None)
        spec = getattr(pod_obj, "spec", None)
        status = getattr(pod_obj, "status", None)

        pod_info: Dict[str, Any] = {
            "name": getattr(meta, "name", pod_name) if meta else pod_name,
            "namespace": getattr(meta, "namespace", namespace) if meta else namespace,
            "uid": getattr(meta, "uid", "") if meta else "",
            "creation_timestamp": str(getattr(meta, "creation_timestamp", "")) if meta else "",
            "labels": getattr(meta, "labels", {}) or {} if meta else {},
            "annotations": getattr(meta, "annotations", {}) or {} if meta else {},
            "owner_references": [],
            "phase": getattr(status, "phase", "Unknown") if status else "Unknown",
            "pod_ip": getattr(status, "pod_ip", "") if status else "",
            "host_ip": getattr(status, "host_ip", "") if status else "",
            "node_name": getattr(status, "node_name", "") or getattr(spec, "node_name", "") if (status or spec) else "",
            "start_time": str(getattr(status, "start_time", "")) if status else "",
            "conditions": [],
            "containers": [],
            "init_containers": [],
            "volumes": [],
        }

        # Extract owner references
        if meta and hasattr(meta, "owner_references") and meta.owner_references:
            for owner in meta.owner_references:
                pod_info["owner_references"].append({
                    "kind": getattr(owner, "kind", ""),
                    "name": getattr(owner, "name", ""),
                    "uid": getattr(owner, "uid", ""),
                    "controller": getattr(owner, "controller", False),
                })

        # Extract conditions
        if status and hasattr(status, "conditions") and status.conditions:
            for c in status.conditions:
                pod_info["conditions"].append({
                    "type": getattr(c, "type", ""),
                    "status": getattr(c, "status", ""),
                    "reason": getattr(c, "reason", ""),
                    "message": getattr(c, "message", ""),
                    "last_transition_time": str(getattr(c, "last_transition_time", "")),
                })

        findings: List[Dict[str, Any]] = []
        configmap_names = set()
        secret_names = set()

        # Helper to parse container status
        def parse_container_statuses(c_specs: Any, c_statuses: Any, is_init: bool = False) -> List[Dict[str, Any]]:
            result = []
            status_map = {}
            if c_statuses:
                for cs in c_statuses:
                    status_map[getattr(cs, "name", "")] = cs

            for cs_spec in (c_specs or []):
                c_name = getattr(cs_spec, "name", "")
                c_image = getattr(cs_spec, "image", "")
                cs_status = status_map.get(c_name)

                c_info = {
                    "name": c_name,
                    "image": c_image,
                    "image_id": getattr(cs_status, "image_id", "") if cs_status else "",
                    "ready": getattr(cs_status, "ready", False) if cs_status else False,
                    "restart_count": getattr(cs_status, "restart_count", 0) if cs_status else 0,
                    "state": "unknown",
                    "state_detail": {},
                }

                if cs_status and hasattr(cs_status, "state") and cs_status.state:
                    state_obj = cs_status.state
                    if hasattr(state_obj, "running") and state_obj.running:
                        c_info["state"] = "running"
                        c_info["state_detail"] = {
                            "started_at": str(getattr(state_obj.running, "started_at", ""))
                        }
                    elif hasattr(state_obj, "waiting") and state_obj.waiting:
                        c_info["state"] = "waiting"
                        reason = getattr(state_obj.waiting, "reason", "")
                        message = getattr(state_obj.waiting, "message", "")
                        c_info["state_detail"] = {
                            "reason": reason,
                            "message": message,
                        }
                        findings.append({
                            "severity": "CRITICAL" if "BackOff" in reason or "Error" in reason or reason == "ErrImagePull" else "WARNING",
                            "category": "CONTAINER",
                            "message": f"Container '{c_name}' in pod '{pod_name}' is waiting: {reason} ({message})",
                            "evidence": [f"image: {c_image}", f"reason: {reason}", f"message: {message}"]
                        })
                    elif hasattr(state_obj, "terminated") and state_obj.terminated:
                        c_info["state"] = "terminated"
                        term = state_obj.terminated
                        reason = getattr(term, "reason", "")
                        exit_code = getattr(term, "exit_code", 0)
                        message = getattr(term, "message", "")
                        c_info["state_detail"] = {
                            "reason": reason,
                            "exit_code": exit_code,
                            "signal": getattr(term, "signal", None),
                            "message": message,
                            "finished_at": str(getattr(term, "finished_at", "")),
                        }
                        if exit_code != 0 or reason == "OOMKilled":
                            findings.append({
                                "severity": "CRITICAL",
                                "category": "CONTAINER",
                                "message": f"Container '{c_name}' in pod '{pod_name}' terminated unexpectedly with exit code {exit_code} (reason: {reason})",
                                "evidence": [f"image: {c_image}", f"exit_code: {exit_code}", f"reason: {reason}"]
                            })

                if cs_status and getattr(cs_status, "restart_count", 0) > 3:
                    findings.append({
                        "severity": "WARNING",
                        "category": "CONTAINER",
                        "message": f"Container '{c_name}' has restarted {cs_status.restart_count} times",
                        "evidence": [f"restart_count: {cs_status.restart_count}"]
                    })

                # Check env variables for ConfigMap/Secret references
                if hasattr(cs_spec, "env") and cs_spec.env:
                    for env_var in cs_spec.env:
                        value_from = getattr(env_var, "value_from", None)
                        if value_from:
                            cm_ref = getattr(value_from, "config_map_key_ref", None)
                            if cm_ref and getattr(cm_ref, "name", None):
                                configmap_names.add(cm_ref.name)

                            sec_ref = getattr(value_from, "secret_key_ref", None)
                            if sec_ref and getattr(sec_ref, "name", None):
                                secret_names.add(sec_ref.name)

                if hasattr(cs_spec, "env_from") and cs_spec.env_from:
                    for env_from in cs_spec.env_from:
                        cm_ref = getattr(env_from, "config_map_ref", None)
                        if cm_ref and getattr(cm_ref, "name", None):
                            configmap_names.add(cm_ref.name)

                        sec_ref = getattr(env_from, "secret_ref", None)
                        if sec_ref and getattr(sec_ref, "name", None):
                            secret_names.add(sec_ref.name)

                result.append(c_info)
            return result

        if spec:
            c_statuses = getattr(status, "container_statuses", []) if status else []
            pod_info["containers"] = parse_container_statuses(getattr(spec, "containers", []), c_statuses)

            init_statuses = getattr(status, "init_container_statuses", []) if status else []
            pod_info["init_containers"] = parse_container_statuses(getattr(spec, "init_containers", []), init_statuses, is_init=True)

            # Inspect volumes
            if hasattr(spec, "volumes") and spec.volumes:
                for vol in spec.volumes:
                    v_name = getattr(vol, "name", "")
                    v_detail: Dict[str, Any] = {"name": v_name}

                    if hasattr(vol, "persistent_volume_claim") and vol.persistent_volume_claim:
                        claim_name = getattr(vol.persistent_volume_claim, "claim_name", "")
                        v_detail["type"] = "persistentVolumeClaim"
                        v_detail["claim_name"] = claim_name
                    elif hasattr(vol, "config_map") and vol.config_map:
                        cm_name = getattr(vol.config_map, "name", "")
                        v_detail["type"] = "configMap"
                        v_detail["configmap_name"] = cm_name
                        if cm_name:
                            configmap_names.add(cm_name)
                    elif hasattr(vol, "secret") and vol.secret:
                        sec_name = getattr(vol.secret, "secret_name", "")
                        v_detail["type"] = "secret"
                        v_detail["secret_name"] = sec_name
                        if sec_name:
                            secret_names.add(sec_name)
                    elif hasattr(vol, "host_path") and vol.host_path:
                        v_detail["type"] = "hostPath"
                        v_detail["path"] = getattr(vol.host_path, "path", "")
                    elif hasattr(vol, "empty_dir") and vol.empty_dir is not None:
                        v_detail["type"] = "emptyDir"
                    else:
                        v_detail["type"] = "other"

                    pod_info["volumes"].append(v_detail)

        configmaps_ref = [{"name": name, "namespace": namespace} for name in configmap_names]
        # SECRETS METADATA ONLY - NO VALUES!
        secrets_ref = [{"name": name, "namespace": namespace} for name in secret_names]

        return pod_info, configmaps_ref, secrets_ref, findings
