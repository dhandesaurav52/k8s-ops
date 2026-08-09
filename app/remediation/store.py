import json
import logging
import os
import threading
from typing import Dict, List, Optional

from app.remediation.models import AuditRecord, RemediationPlan

logger = logging.getLogger("SkyOps.RemediationStore")

DEFAULT_REMEDIATION_FILE = os.path.join("data", "remediations.json")
DEFAULT_AUDIT_FILE = os.path.join("data", "remediation_audit.json")


class RemediationStore:
    """
    Thread-safe persistent storage for Remediation Plans and Audit Trail.
    """

    def __init__(self, filepath: str = DEFAULT_REMEDIATION_FILE, audit_filepath: str = DEFAULT_AUDIT_FILE):
        self.filepath = filepath
        self.audit_filepath = audit_filepath
        self._lock = threading.Lock()
        self._plans: Dict[str, RemediationPlan] = {}
        self._audit_records: List[AuditRecord] = []
        self._load()

    def _load(self):
        with self._lock:
            # Load Plans
            if os.path.exists(self.filepath):
                try:
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                plan = RemediationPlan.from_dict(item)
                                self._plans[plan.remediation_id] = plan
                except Exception as e:
                    logger.error(f"Failed to load remediation plans from {self.filepath}: {e}")

            # Load Audit
            if os.path.exists(self.audit_filepath):
                try:
                    with open(self.audit_filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            self._audit_records = [AuditRecord(**item) for item in data]
                except Exception as e:
                    logger.error(f"Failed to load remediation audit records from {self.audit_filepath}: {e}")

    def _flush_plans(self):
        data_dir = os.path.dirname(self.filepath)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)

        try:
            plans_list = [p.to_dict() for p in self._plans.values()]
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(plans_list, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to flush remediation plans to {self.filepath}: {e}")

    def _flush_audit(self):
        data_dir = os.path.dirname(self.audit_filepath)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)

        try:
            records_list = [r.to_dict() for r in self._audit_records]
            with open(self.audit_filepath, "w", encoding="utf-8") as f:
                json.dump(records_list, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to flush remediation audit records to {self.audit_filepath}: {e}")

    def save_plan(self, plan: RemediationPlan):
        with self._lock:
            self._plans[plan.remediation_id] = plan
            self._flush_plans()

    def get_plan(self, remediation_id: str) -> Optional[RemediationPlan]:
        with self._lock:
            return self._plans.get(remediation_id)

    def get_plan_for_incident(self, incident_id: str) -> Optional[RemediationPlan]:
        with self._lock:
            for p in self._plans.values():
                if p.incident_id == incident_id:
                    return p
            return None

    def list_plans(self, cluster_id: Optional[str] = None) -> List[RemediationPlan]:
        with self._lock:
            plans = list(self._plans.values())
            if cluster_id and cluster_id != "ALL":
                plans = [p for p in plans if p.cluster_id == cluster_id]
            # Sort newest created first
            plans.sort(key=lambda x: x.created_at, reverse=True)
            return plans

    def save_audit_record(self, record: AuditRecord):
        with self._lock:
            self._audit_records.append(record)
            self._flush_audit()

    def list_audit_records(self, cluster_id: Optional[str] = None) -> List[AuditRecord]:
        with self._lock:
            records = list(self._audit_records)
            if cluster_id and cluster_id != "ALL":
                records = [r for r in records if r.cluster_id == cluster_id]
            records.sort(key=lambda x: x.timestamp, reverse=True)
            return records
