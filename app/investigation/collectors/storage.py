import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("SkyOps.StorageCollector")


class StorageCollector:
    """
    Collects storage chain evidence: Pod -> PVC -> PV -> StorageClass.
    """

    @staticmethod
    def collect(
        v1_api: Any,
        storage_v1_api: Any,
        namespace: str,
        pod_name: str,
        volumes: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], List[Dict[str, str]], List[Dict[str, Any]]]:
        """
        Returns: (storage_summary, relationships, findings)
        """
        storage_summary: Dict[str, Any] = {
            "pvcs": [],
            "pvs": [],
            "storage_classes": [],
            "status": "SUCCESS"
        }
        relationships = []
        findings = []

        if not volumes:
            return storage_summary, relationships, findings

        pvc_claims = [v["claim_name"] for v in volumes if v.get("type") == "persistentVolumeClaim" and v.get("claim_name")]

        if not pvc_claims:
            return storage_summary, relationships, findings

        sc_seen = set()

        for claim_name in pvc_claims:
            relationships.append({
                "from": f"Pod/{namespace}/{pod_name}",
                "relationship": "REFERENCES",
                "to": f"PVC/{namespace}/{claim_name}"
            })

            pvc_info: Dict[str, Any] = {"name": claim_name, "namespace": namespace}
            pv_name = None

            if v1_api:
                try:
                    pvc = v1_api.read_namespaced_persistent_volume_claim(name=claim_name, namespace=namespace)
                    meta = getattr(pvc, "metadata", None)
                    spec = getattr(pvc, "spec", None)
                    status = getattr(pvc, "status", None)

                    phase = getattr(status, "phase", "Unknown") if status else "Unknown"
                    pv_name = getattr(spec, "volume_name", "") if spec else ""
                    sc_name = getattr(spec, "storage_class_name", "") if spec else ""

                    pvc_info.update({
                        "uid": getattr(meta, "uid", "") if meta else "",
                        "phase": phase,
                        "volume_name": pv_name,
                        "storage_class": sc_name,
                        "access_modes": getattr(spec, "access_modes", []) if spec else [],
                        "requests": getattr(spec, "resources", {}).requests if (spec and hasattr(spec, "resources") and spec.resources) else {},
                        "creation_timestamp": str(getattr(meta, "creation_timestamp", "")) if meta else "",
                    })

                    if phase != "Bound":
                        findings.append({
                            "severity": "CRITICAL",
                            "category": "STORAGE",
                            "message": f"PersistentVolumeClaim '{claim_name}' in namespace '{namespace}' is in phase '{phase}' (not Bound)",
                            "evidence": [f"pvc: {claim_name}", f"phase: {phase}"]
                        })

                    if sc_name:
                        sc_seen.add(sc_name)

                except Exception as e:
                    logger.warning(f"Could not read PVC {namespace}/{claim_name}: {e}")
                    pvc_info["error"] = str(e)
                    findings.append({
                        "severity": "WARNING",
                        "category": "STORAGE",
                        "message": f"Could not inspect PVC '{claim_name}': {e}",
                        "evidence": [str(e)]
                    })

            storage_summary["pvcs"].append(pvc_info)

            # Inspect PV if bound
            if pv_name and v1_api:
                relationships.append({
                    "from": f"PVC/{namespace}/{claim_name}",
                    "relationship": "BOUND_TO",
                    "to": f"PV/{pv_name}"
                })

                pv_info: Dict[str, Any] = {"name": pv_name}
                try:
                    pv = v1_api.read_persistent_volume(name=pv_name)
                    pv_meta = getattr(pv, "metadata", None)
                    pv_spec = getattr(pv, "spec", None)
                    pv_status = getattr(pv, "status", None)

                    pv_sc = getattr(pv_spec, "storage_class_name", "") if pv_spec else ""
                    if pv_sc:
                        sc_seen.add(pv_sc)

                    csi_driver = ""
                    if pv_spec and hasattr(pv_spec, "csi") and pv_spec.csi:
                        csi_driver = getattr(pv_spec.csi, "driver", "")

                    pv_info.update({
                        "uid": getattr(pv_meta, "uid", "") if pv_meta else "",
                        "phase": getattr(pv_status, "phase", "Unknown") if pv_status else "Unknown",
                        "capacity": getattr(pv_spec, "capacity", {}) if pv_spec else {},
                        "reclaim_policy": getattr(pv_spec, "persistent_volume_reclaim_policy", "") if pv_spec else "",
                        "storage_class": pv_sc,
                        "csi_driver": csi_driver,
                        "creation_timestamp": str(getattr(pv_meta, "creation_timestamp", "")) if pv_meta else "",
                    })
                except Exception as e:
                    logger.warning(f"Could not read PV {pv_name}: {e}")
                    pv_info["error"] = str(e)

                storage_summary["pvs"].append(pv_info)

        # Inspect StorageClasses
        for sc_name in sc_seen:
            sc_info: Dict[str, Any] = {"name": sc_name}
            if storage_v1_api:
                try:
                    sc = storage_v1_api.read_storage_class(name=sc_name)
                    sc_meta = getattr(sc, "metadata", None)
                    sc_info.update({
                        "provisioner": getattr(sc, "provisioner", ""),
                        "reclaim_policy": getattr(sc, "reclaim_policy", ""),
                        "volume_binding_mode": getattr(sc, "volume_binding_mode", ""),
                        "allow_volume_expansion": getattr(sc, "allow_volume_expansion", False),
                        "creation_timestamp": str(getattr(sc_meta, "creation_timestamp", "")) if sc_meta else "",
                    })
                    relationships.append({
                        "from": f"PV/{pv_name if 'pv_name' in locals() and pv_name else 'unknown'}",
                        "relationship": "PROVISIONED_BY",
                        "to": f"StorageClass/{sc_name}"
                    })
                except Exception as e:
                    logger.warning(f"Could not read StorageClass {sc_name}: {e}")
                    sc_info["error"] = str(e)

            storage_summary["storage_classes"].append(sc_info)

        return storage_summary, relationships, findings
