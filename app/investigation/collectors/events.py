import logging
from typing import Any, Dict, List, Optional
from app.kubernetes.collector import sanitize_text

logger = logging.getLogger("SkyOps.EventsCollector")


class EventsCollector:
    """
    Collects Kubernetes events related to Pod, ReplicaSet, Deployment, Node, and PVC.
    Sanitizes all text to prevent credential/secret leakage.
    """

    @staticmethod
    def collect(
        v1_api: Any,
        namespace: str,
        involved_objects: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        involved_objects: list of {"kind": "Pod|ReplicaSet|Deployment|Node|PersistentVolumeClaim", "name": "..."}
        Returns: list of event dicts
        """
        if not v1_api or not involved_objects:
            return []

        events = []
        seen_event_uids = set()

        for obj in involved_objects:
            kind = obj.get("kind", "")
            name = obj.get("name", "")
            if not kind or not name:
                continue

            try:
                if kind == "Node":
                    event_list = v1_api.list_event_for_all_namespaces(
                        field_selector=f"involvedObject.name={name},involvedObject.kind=Node"
                    )
                else:
                    event_list = v1_api.list_namespaced_event(
                        namespace=namespace,
                        field_selector=f"involvedObject.name={name},involvedObject.kind={kind}"
                    )

                for item in event_list.items:
                    meta = getattr(item, "metadata", None)
                    uid = getattr(meta, "uid", f"{item.reason}-{item.message}") if meta else f"{item.reason}-{item.message}"

                    if uid in seen_event_uids:
                        continue
                    seen_event_uids.add(uid)

                    inv_obj = getattr(item, "involved_object", None)
                    inv_dict = {}
                    if inv_obj:
                        inv_dict = {
                            "kind": getattr(inv_obj, "kind", ""),
                            "name": getattr(inv_obj, "name", ""),
                            "namespace": getattr(inv_obj, "namespace", namespace),
                        }

                    event_entry = {
                        "type": getattr(item, "type", "Normal") or "Normal",
                        "reason": getattr(item, "reason", "Unknown") or "Unknown",
                        "message": sanitize_text(getattr(item, "message", "") or ""),
                        "count": getattr(item, "count", 1) or 1,
                        "first_timestamp": str(getattr(item, "first_timestamp", "")) if getattr(item, "first_timestamp", None) else "",
                        "last_timestamp": str(getattr(item, "last_timestamp", "")) if getattr(item, "last_timestamp", None) else "",
                        "involved_object": inv_dict,
                        "source": getattr(getattr(item, "source", None), "component", "") if hasattr(item, "source") else "",
                    }
                    events.append(event_entry)

            except Exception as e:
                logger.debug(f"Could not collect events for {kind}/{name}: {e}")

        # Sort events by last_timestamp or first_timestamp descending
        events.sort(key=lambda x: x.get("last_timestamp") or x.get("first_timestamp") or "", reverse=True)
        return events
