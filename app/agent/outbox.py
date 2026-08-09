import json
import logging
import os
import time
import uuid
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Dict, List, Optional

logger = logging.getLogger("SkyOps.Outbox")


class OutboxQueue:
    """
    Durable, thread-safe local Outbox Queue for incident synchronization.
    Ensures zero blocking on Kubernetes incident detection when SkyOps Cloud is offline/unreachable.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent / "data"
            base_dir.mkdir(parents=True, exist_ok=True)
            storage_path = base_dir / "outbox.json"

        self.storage_path = Path(storage_path)
        self.lock = Lock()
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        with self.lock:
            if not self.storage_path.exists():
                self.storage_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.storage_path, "w", encoding="utf-8") as f:
                    json.dump([], f)

    def _read_items(self) -> List[Dict[str, Any]]:
        try:
            if not self.storage_path.exists():
                return []
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read outbox storage '{self.storage_path}': {e}")
            return []

    def _write_items(self, items: List[Dict[str, Any]]):
        try:
            temp_file = self.storage_path.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2)
            temp_file.replace(self.storage_path)
        except Exception as e:
            logger.error(f"Failed to write outbox storage '{self.storage_path}': {e}")

    def enqueue(self, payload: Dict[str, Any]) -> str:
        """Enqueue an incident synchronization payload."""
        item_id = str(uuid.uuid4())
        now = time.time()
        item = {
            "id": item_id,
            "type": "INCIDENT_SYNC",
            "payload": payload,
            "status": "PENDING",  # PENDING | COMPLETED | FAILED
            "attempts": 0,
            "created_at": now,
            "next_retry_at": now,
            "last_error": None,
        }

        with self.lock:
            items = self._read_items()
            
            # Deduplicate pending items for the same incident_id & cluster_id if already queued
            inc_id = payload.get("incident_id")
            cluster_id = payload.get("cluster_id")
            if inc_id and cluster_id:
                for existing in items:
                    if (
                        existing.get("status") == "PENDING"
                        and existing.get("payload", {}).get("incident_id") == inc_id
                        and existing.get("payload", {}).get("cluster_id") == cluster_id
                    ):
                        # Update existing pending item with newer payload
                        existing["payload"] = payload
                        existing["next_retry_at"] = now
                        self._write_items(items)
                        logger.debug(f"Updated queued outbox item for incident '{inc_id}'.")
                        return existing["id"]

            items.append(item)
            self._write_items(items)

        logger.info(f"Queued incident '{payload.get('incident_id', 'UNKNOWN')}' in Outbox ({item_id}).")
        return item_id

    def get_pending(self) -> List[Dict[str, Any]]:
        """Retrieve all items ready to be processed."""
        now = time.time()
        with self.lock:
            items = self._read_items()
            pending = [
                i for i in items
                if i.get("status") == "PENDING" and i.get("next_retry_at", 0) <= now
            ]
            return pending

    def mark_completed(self, item_id: str):
        """Mark an outbox item as completed (or remove it)."""
        with self.lock:
            items = self._read_items()
            updated = [i for i in items if i.get("id") != item_id]
            self._write_items(updated)
        logger.debug(f"Outbox item {item_id} marked COMPLETED.")

    def mark_failed(self, item_id: str, error: str, max_retries: int = 10):
        """Mark an outbox item as failed with exponential backoff for retries."""
        now = time.time()
        with self.lock:
            items = self._read_items()
            for item in items:
                if item.get("id") == item_id:
                    attempts = item.get("attempts", 0) + 1
                    item["attempts"] = attempts
                    item["last_error"] = str(error)

                    if attempts >= max_retries:
                        item["status"] = "FAILED"
                        logger.error(f"Outbox item {item_id} reached max retries ({max_retries}). Marked FAILED.")
                    else:
                        backoff = min(300.0, 2.0 ** attempts)  # Max 5 min backoff
                        item["next_retry_at"] = now + backoff
                        logger.warning(
                            f"Outbox item {item_id} sync failed (attempt {attempts}/{max_retries}). "
                            f"Next retry in {backoff:.1f}s."
                        )
                    break
            self._write_items(items)

    def list_all(self) -> List[Dict[str, Any]]:
        with self.lock:
            return self._read_items()

    def clear(self):
        with self.lock:
            self._write_items([])


class CloudSyncWorker(Thread):
    """
    Background worker thread that processes outbox items asynchronously
    without blocking the core Kubernetes monitoring loop.
    """

    def __init__(self, outbox: OutboxQueue, connector: Any, poll_interval: float = 2.0):
        super().__init__(daemon=True, name="SkyOps-CloudSyncWorker")
        self.outbox = outbox
        self.connector = connector
        self.poll_interval = poll_interval
        self.running = False

    def run(self):
        self.running = True
        logger.info("CloudSyncWorker thread started.")

        while self.running:
            try:
                pending_items = self.outbox.get_pending()
                for item in pending_items:
                    if not self.running:
                        break
                    
                    item_id = item["id"]
                    payload = item.get("payload", {})

                    success = self.connector.send_incident(payload)
                    if success:
                        self.outbox.mark_completed(item_id)
                    else:
                        self.outbox.mark_failed(item_id, error="Cloud connector delivery failed")

            except Exception as e:
                logger.error(f"Unhandled error in CloudSyncWorker loop: {e}", exc_info=True)

            time.sleep(self.poll_interval)

        logger.info("CloudSyncWorker thread stopped.")

    def stop(self):
        self.running = False
