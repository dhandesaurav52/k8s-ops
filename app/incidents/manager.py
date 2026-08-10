import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from kubernetes import client

from app.ai.analyzer import AIAnalyzer
from app.ai.sanitizer import EvidenceSanitizer
from app.correlation.engine import CorrelationEngine
from app.diagnosis.engine import DiagnosisEngine
from app.incidents.models import Incident, ResourceRef, utc_now_iso
from app.incidents.store import IncidentStore
from app.investigation.engine import InvestigationEngine
from app.investigation.models import InvestigationResult
from app.kubernetes.collector import collect_pod_events, get_pod_unhealthy_state, is_pod_confirmed_healthy

logger = logging.getLogger("SkyOps.IncidentManager")


def compute_pod_canonical_state(pod: Any, primary_reason: str, current_state: str) -> str:
    """
    Computes a deterministic canonical state string for a Pod's current incident state.
    Ignores volatile metadata like resourceVersion, event timestamps, watch timestamps,
    and dynamic container waiting messages (e.g., exponential backoff timers).
    """
    if not pod or not hasattr(pod, "metadata") or not pod.metadata:
        return f"reason={primary_reason}|state={current_state}"

    uid = getattr(pod.metadata, "uid", "") or ""
    phase = getattr(getattr(pod, "status", None), "phase", "") or "Unknown"

    container_details = []
    if hasattr(pod, "status") and pod.status:
        container_statuses = (getattr(pod.status, "container_statuses", None) or []) + \
                             (getattr(pod.status, "init_container_statuses", None) or [])
        for cs in container_statuses:
            c_name = getattr(cs, "name", "unknown")
            state = getattr(cs, "state", None)
            if state:
                waiting = getattr(state, "waiting", None)
                terminated = getattr(state, "terminated", None)
                if waiting and getattr(waiting, "reason", None):
                    reason = getattr(waiting, "reason", "")
                    container_details.append(f"{c_name}:waiting:{reason}")
                elif terminated and (getattr(terminated, "reason", None) or getattr(terminated, "exit_code", None) is not None):
                    reason = getattr(terminated, "reason", "") or f"ExitCode{getattr(terminated, 'exit_code', '')}"
                    container_details.append(f"{c_name}:terminated:{reason}")

    c_str = "|".join(sorted(container_details)) if container_details else current_state
    return f"uid={uid}|phase={phase}|reason={primary_reason}|containers={c_str}"


class IncidentManager:
    """
    Core Incident Lifecycle Engine.
    Coordinates health checks, deduplication, state transitions, diagnosis,
    deep investigation, AI reasoning, storage persistence, and cloud outbox sync.
    """

    def __init__(
        self,
        store: IncidentStore,
        k8s_client: Optional[client.CoreV1Api] = None,
        apps_v1_api: Optional[client.AppsV1Api] = None,
        storage_v1_api: Optional[client.StorageV1Api] = None,
        investigation_engine: Optional[InvestigationEngine] = None,
        ai_analyzer: Optional[AIAnalyzer] = None,
        outbox: Optional[Any] = None,
        cluster_id: Optional[str] = None,
    ):
        self.store = store
        self.k8s_client = k8s_client
        self.apps_v1_api = apps_v1_api
        self.storage_v1_api = storage_v1_api
        self.investigation_engine = investigation_engine or InvestigationEngine(
            v1_api=k8s_client,
            apps_v1_api=apps_v1_api,
            storage_v1_api=storage_v1_api,
        )
        self.ai_analyzer = ai_analyzer or AIAnalyzer()
        self.outbox = outbox
        self.cluster_id = cluster_id or os.getenv("SKYOPS_CLUSTER_ID", "skyops-cluster-default")
        self._lock = threading.Lock()

    def _notify_outbox(self, incident: Incident) -> None:
        """Enqueue sanitized incident payload into Outbox for async Cloud sync."""
        if not self.outbox:
            return
        try:
            severity = "MEDIUM"
            if isinstance(incident.diagnosis, dict):
                severity = incident.diagnosis.get("severity", "MEDIUM")

            payload = {
                "cluster_id": self.cluster_id,
                "incident_id": incident.incident_id,
                "resource_kind": incident.resource.kind,
                "resource_namespace": incident.resource.namespace,
                "resource_name": incident.resource.name,
                "resource_uid": incident.resource.uid,
                "category": incident.category,
                "status": incident.status,
                "current_state": incident.current_state,
                "severity": severity,
                "occurrences": incident.occurrences,
                "first_seen": incident.created_at,
                "last_seen": incident.last_seen,
                "resolved_at": incident.resolved_at,
                "diagnosis": incident.diagnosis,
                "investigation": incident.investigation,
                "ai_analysis": incident.ai_analysis,
                "state_history": incident.state_history,
            }
            sanitized = EvidenceSanitizer._sanitize_recursive(payload)
            self.outbox.enqueue(sanitized)
        except Exception as e:
            logger.error(f"Failed to enqueue incident '{incident.incident_id}' to outbox: {e}")

    def process_pod_event(self, event_type: str, pod: Any) -> Optional[Incident]:
        """
        Process a Kubernetes Pod Watch Event (ADDED, MODIFIED, DELETED).
        Detects failures, creates or updates incidents, attaches deep investigation,
        and handles recovery. Thread-safe execution prevents races on rapid events.
        """
        if not pod or not hasattr(pod, "metadata") or not pod.metadata:
            return None

        with self._lock:
            namespace = pod.metadata.namespace or "default"
            name = pod.metadata.name or "unknown"
            uid = pod.metadata.uid or f"{namespace}-{name}"
            resource_ref = ResourceRef(kind="Pod", name=name, namespace=namespace, uid=uid)

            is_unhealthy, primary_reason, current_state = get_pod_unhealthy_state(pod)

            # Compute stable deduplication identity key for this resource failure
            identity_key = Incident.compute_identity_key(namespace, "Pod", uid, primary_reason)

            # Check if there is an existing OPEN incident for this resource instance or identity key
            existing_incident = self.store.find_open_for_resource(
                namespace, "Pod", uid, identity_key=identity_key, name=name
            )

            # -------------------------------------------------------------
            # SCENARIO A: Workload is UNHEALTHY
            # -------------------------------------------------------------
            if is_unhealthy:
                canonical_state = compute_pod_canonical_state(pod, primary_reason, current_state)

                if existing_incident:
                    prev_canonical = (
                        existing_incident.last_canonical_state
                        or f"uid={uid}|phase={getattr(getattr(pod, 'status', None), 'phase', '') or 'Unknown'}|reason={existing_incident.category}|containers={existing_incident.current_state}"
                    )

                    # State comparison: ignore if canonical state is identical
                    if canonical_state == prev_canonical:
                        logger.debug(
                            f"Ignoring duplicate Kubernetes event for {namespace}/{name} (State unchanged: {primary_reason})"
                        )
                        return existing_incident

                    # Meaningful state transition / update
                    existing_incident.category = primary_reason
                    existing_incident.identity_key = identity_key
                    existing_incident.last_canonical_state = canonical_state
                    existing_incident.occurrences += 1
                    existing_incident.last_seen = utc_now_iso()
                    existing_incident.updated_at = utc_now_iso()

                    # Add to state history if state changed
                    last_item = existing_incident.state_history[-1] if existing_incident.state_history else None
                    last_st = last_item.get("state") if isinstance(last_item, dict) else (str(last_item) if last_item is not None else None)
                    if not existing_incident.state_history or last_st != primary_reason:
                        existing_incident.state_history.append(primary_reason)

                    existing_incident.current_state = current_state
                    events = collect_pod_events(self.k8s_client, namespace, name, uid)
                    diagnosis, recommendations = DiagnosisEngine.diagnose(primary_reason, current_state, events, pod_obj=pod)
                    existing_incident.evidence = events
                    existing_incident.diagnosis = diagnosis
                    existing_incident.recommendations = recommendations

                    # Run Deep Investigation
                    if self.investigation_engine:
                        inv_res = self.investigation_engine.investigate(existing_incident, pod_obj=pod)
                        existing_incident.investigation = inv_res.to_dict()

                    # Run Signal Correlation & Evidence-Based RCA
                    corr_res = CorrelationEngine.correlate(
                        incident=existing_incident,
                        investigation=existing_incident.investigation,
                        existing_incidents=self.store.list_all(),
                    )
                    existing_incident.investigation["evidence_timeline"] = corr_res.evidence_timeline
                    existing_incident.investigation["root_cause_analysis"] = corr_res.root_cause_analysis
                    existing_incident.investigation["blast_radius"] = corr_res.blast_radius
                    existing_incident.investigation["related_incidents"] = corr_res.related_incidents
                    if isinstance(existing_incident.diagnosis, dict):
                        existing_incident.diagnosis["confidence_score"] = corr_res.root_cause_analysis["confidence_score"]
                        existing_incident.diagnosis["confidence_level"] = corr_res.root_cause_analysis["confidence_level"]
                        existing_incident.diagnosis["confidence"] = corr_res.root_cause_analysis["confidence_score"] / 100.0

                    # Run AI Analysis if triggered
                    if self.ai_analyzer:
                        self.ai_analyzer.analyze_incident(existing_incident)

                    self.store.save(existing_incident)
                    self._notify_outbox(existing_incident)
                    self.log_terminal_update(existing_incident, "UPDATED")
                    return existing_incident
                else:
                    # Create NEW Incident
                    events = collect_pod_events(self.k8s_client, namespace, name, uid)
                    diagnosis, recommendations = DiagnosisEngine.diagnose(primary_reason, current_state, events, pod_obj=pod)
                    new_id = self.store.generate_next_id()
                    new_incident = Incident(
                        incident_id=new_id,
                        status="OPEN",
                        resource=resource_ref,
                        category=primary_reason,
                        current_state=current_state,
                        occurrences=1,
                        created_at=utc_now_iso(),
                        updated_at=utc_now_iso(),
                        last_seen=utc_now_iso(),
                        state_history=[primary_reason],
                        evidence=events,
                        diagnosis=diagnosis,
                        recommendations=recommendations,
                        identity_key=identity_key,
                        last_canonical_state=canonical_state,
                    )

                    # Run Deep Investigation
                    if self.investigation_engine:
                        inv_res = self.investigation_engine.investigate(new_incident, pod_obj=pod)
                        new_incident.investigation = inv_res.to_dict()

                    # Run Signal Correlation & Evidence-Based RCA
                    corr_res = CorrelationEngine.correlate(
                        incident=new_incident,
                        investigation=new_incident.investigation,
                        existing_incidents=self.store.list_all(),
                    )
                    new_incident.investigation["evidence_timeline"] = corr_res.evidence_timeline
                    new_incident.investigation["root_cause_analysis"] = corr_res.root_cause_analysis
                    new_incident.investigation["blast_radius"] = corr_res.blast_radius
                    new_incident.investigation["related_incidents"] = corr_res.related_incidents
                    if isinstance(new_incident.diagnosis, dict):
                        new_incident.diagnosis["confidence_score"] = corr_res.root_cause_analysis["confidence_score"]
                        new_incident.diagnosis["confidence_level"] = corr_res.root_cause_analysis["confidence_level"]
                        new_incident.diagnosis["confidence"] = corr_res.root_cause_analysis["confidence_score"] / 100.0

                    # Run AI Analysis
                    if self.ai_analyzer:
                        self.ai_analyzer.analyze_incident(new_incident)

                    self.store.save(new_incident)
                    self._notify_outbox(new_incident)
                    self.log_terminal_update(new_incident, "DETECTED")
                    return new_incident

            # -------------------------------------------------------------
            # SCENARIO B: Workload has RECOVERED (Running + Ready)
            # -------------------------------------------------------------
            else:
                if not is_pod_confirmed_healthy(pod):
                    # Pod is in transient or unconfirmed state (e.g. ContainerCreating or Running but not Ready)
                    # Do NOT resolve open incidents prematurely
                    return existing_incident

                # Look for ANY open incident for this resource UID/namespace/name
                open_incidents = [
                    inc for inc in self.store.list_all()
                    if inc.status == "OPEN"
                    and inc.resource.namespace == namespace
                    and (inc.resource.uid == uid or inc.resource.name == name)
                ]

                for open_inc in open_incidents:
                    now_str = utc_now_iso()
                    open_inc.status = "RESOLVED"
                    open_inc.resolved_at = now_str
                    open_inc.updated_at = now_str
                    open_inc.last_seen = now_str
                    open_inc.last_canonical_state = "RESOLVED"
                    last_item = open_inc.state_history[-1] if open_inc.state_history else None
                    last_st = last_item.get("state") if isinstance(last_item, dict) else (str(last_item) if last_item is not None else None)
                    if not open_inc.state_history or last_st != "Running":
                        open_inc.state_history.append("Running")

                    self.store.save(open_inc)
                    self._notify_outbox(open_inc)
                    self.log_terminal_update(open_inc, "RESOLVED")

                return None


    def log_terminal_update(self, incident: Incident, action: str) -> None:
        """
        Formats human-readable logs to stdout as required by design specs.
        """
        if action == "DETECTED":
            print("\n" + "🚨 INCIDENT DETECTED")
            print(f"Incident ID: {incident.incident_id}")
            print(f"Resource: {incident.resource.namespace}/{incident.resource.name}")
            print(f"Category: {incident.category}")
            print(f"State: {incident.current_state}")
            print(f"Severity: {incident.diagnosis.get('severity', 'MEDIUM')}")
            print("------------------------------------------------------------")
            logger.info(f"Incident {incident.incident_id} DETECTED for {incident.resource.namespace}/{incident.resource.name}")
            if incident.investigation:
                inv_obj = InvestigationResult.from_dict(incident.investigation)
                InvestigationEngine.print_investigation_summary(inv_obj)
            if incident.ai_analysis:
                AIAnalyzer.print_ai_analysis_cli(incident)

        elif action == "UPDATED":
            print(f"\nINCIDENT {incident.incident_id} UPDATED")
            print(f"State: {incident.current_state}")
            print(f"Occurrences: {incident.occurrences}")
            print("------------------------------------------------------------")
            logger.info(f"Incident {incident.incident_id} UPDATED (Occurrences: {incident.occurrences})")

        elif action == "RESOLVED":
            print("\n" + "✅ INCIDENT RESOLVED")
            print(f"Incident ID: {incident.incident_id}")
            print(f"Resource: {incident.resource.namespace}/{incident.resource.name}")
            print(f"Resolved At: {incident.resolved_at}")
            print("Final State: Running")
            print("------------------------------------------------------------")
            logger.info(f"Incident {incident.incident_id} RESOLVED for {incident.resource.namespace}/{incident.resource.name}")

