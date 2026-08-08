import json
import logging
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional
from app.incidents.models import Incident

logger = logging.getLogger("SkyOps.IncidentStore")


class IncidentStore:
    """
    Abstract Storage Interface for Incidents.
    Currently backed by local JSON file storage, but easily swappable with PostgreSQL later.
    """

    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        self.lock = threading.Lock()
        self._counter = 0
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """
        Creates directory and file if not present. Reads existing incidents.
        """
        with self.lock:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.file_path.exists():
                self._write_json([])
            else:
                incidents = self._read_json()
                # Find maximum incident number for sequential counter
                max_num = 0
                for inc in incidents:
                    inc_id = inc.get("incident_id", "")
                    if inc_id.startswith("INC-"):
                        try:
                            num = int(inc_id.replace("INC-", ""))
                            if num > max_num:
                                max_num = num
                        except ValueError:
                            pass
                self._counter = max_num

    def _read_json(self) -> List[Dict]:
        try:
            if not self.file_path.exists():
                return []
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return json.loads(content) if content else []
        except Exception as e:
            logger.error(f"Failed to read incidents JSON file: {e}")
            return []

    def _write_json(self, data: List[Dict]) -> None:
        """
        Atomic write using temporary file to prevent file corruption.
        """
        temp_file = self.file_path.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            temp_file.replace(self.file_path)
        except Exception as e:
            logger.error(f"Failed to write incidents JSON file: {e}")
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

    def generate_next_id(self) -> str:
        with self.lock:
            self._counter += 1
            return f"INC-{self._counter:04d}"

    def save(self, incident: Incident) -> None:
        """
        Saves or updates an incident in the JSON store.
        Enforces invariant that at most ONE OPEN incident exists for a given resource UID or identity_key.
        """
        with self.lock:
            incidents_data = self._read_json()
            updated = False
            for i, item in enumerate(incidents_data):
                if item.get("incident_id") == incident.incident_id:
                    incidents_data[i] = incident.to_dict()
                    updated = True
                    break

            if not updated:
                if incident.status == "OPEN":
                    for item in incidents_data:
                        if item.get("status") == "OPEN":
                            res = item.get("resource", {})
                            same_res = (
                                res.get("namespace") == incident.resource.namespace
                                and res.get("kind") == incident.resource.kind
                                and res.get("uid") == incident.resource.uid
                            )
                            same_key = item.get("identity_key") == incident.identity_key
                            if same_res or same_key:
                                logger.warning(
                                    f"Prevented duplicate active incident creation for {incident.resource.namespace}/{incident.resource.name} "
                                    f"(existing={item.get('incident_id')}, duplicate_rejected={incident.incident_id})"
                                )
                                return

                incidents_data.append(incident.to_dict())

            self._write_json(incidents_data)

    def get_by_id(self, incident_id: str) -> Optional[Incident]:
        with self.lock:
            incidents_data = self._read_json()
            for item in incidents_data:
                if item.get("incident_id") == incident_id:
                    return Incident.from_dict(item)
        return None

    def find_open_by_identity(self, identity_key: str) -> Optional[Incident]:
        """
        Looks for an active (OPEN) incident matching the deduplication identity key.
        """
        with self.lock:
            incidents_data = self._read_json()
            for item in incidents_data:
                if item.get("identity_key") == identity_key and item.get("status") == "OPEN":
                    return Incident.from_dict(item)
        return None

    def find_open_for_resource(
        self, namespace: str, kind: str, uid: str, identity_key: Optional[str] = None
    ) -> Optional[Incident]:
        """
        Looks for an active (OPEN) incident matching the resource UID or deduplication identity key.
        Guarantees at most one active incident per Kubernetes resource instance.
        """
        with self.lock:
            incidents_data = self._read_json()
            for item in incidents_data:
                if item.get("status") == "OPEN":
                    res = item.get("resource", {})
                    same_uid = (
                        res.get("namespace") == namespace
                        and res.get("kind") == kind
                        and res.get("uid") == uid
                    )
                    same_key = identity_key and item.get("identity_key") == identity_key
                    if same_uid or same_key:
                        return Incident.from_dict(item)
        return None

    def list_all(self) -> List[Incident]:
        with self.lock:
            incidents_data = self._read_json()
            return [Incident.from_dict(item) for item in incidents_data]
