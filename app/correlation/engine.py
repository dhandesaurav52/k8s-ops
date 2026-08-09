import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.correlation.models import (
    BlastRadius,
    CorrelationResult,
    EvidenceItem,
    RelatedIncident,
    RootCauseAnalysis,
    utc_now_iso,
)
from app.incidents.models import Incident

logger = logging.getLogger("SkyOps.CorrelationEngine")


def parse_iso_time(ts_str: Optional[str]) -> datetime:
    """Safely parses ISO timestamp string to timezone-aware datetime."""
    if not ts_str:
        return datetime.now(timezone.utc)
    try:
        # Handle Z suffix and isoformat
        clean = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


class CorrelationEngine:
    """
    Intelligent Signal Correlation & Evidence-Based RCA Engine.
    Correlates Kubernetes events, state transitions, container details, metrics,
    and logs into a unified timeline, deterministic root cause score, blast radius,
    and related incident graph.
    """

    @classmethod
    def correlate(
        cls,
        incident: Incident,
        investigation: Optional[Dict[str, Any]] = None,
        metrics_summary: Optional[Dict[str, Any]] = None,
        existing_incidents: Optional[List[Incident]] = None,
        window_minutes: int = 5,
    ) -> CorrelationResult:
        """
        Main entry point to execute multi-signal incident correlation.
        Returns complete CorrelationResult.
        """
        inv_dict = investigation or incident.investigation or {}
        if isinstance(inv_dict, dict) and "result" in inv_dict and isinstance(inv_dict["result"], dict):
            inv_dict = inv_dict["result"]

        # 1. Build Chronological Evidence Timeline
        evidence_timeline = cls._build_evidence_timeline(
            incident=incident,
            inv_dict=inv_dict,
            metrics_summary=metrics_summary,
            window_minutes=window_minutes,
        )

        # 2. Perform Evidence-Based Root Cause & Confidence Scoring
        root_cause_analysis = cls._evaluate_root_cause(
            incident=incident,
            inv_dict=inv_dict,
            evidence_timeline=evidence_timeline,
        )

        # 3. Compute Blast Radius & Topology Scope
        blast_radius = cls._calculate_blast_radius(
            incident=incident,
            inv_dict=inv_dict,
        )

        # 4. Identify Related Incidents
        related_incidents = cls._find_related_incidents(
            incident=incident,
            existing_incidents=existing_incidents or [],
        )

        return CorrelationResult(
            incident_id=incident.incident_id,
            evidence_timeline=[e.to_dict() for e in evidence_timeline],
            root_cause_analysis=root_cause_analysis.to_dict(),
            blast_radius=blast_radius.to_dict(),
            related_incidents=[r.to_dict() for r in related_incidents],
            correlation_window_minutes=window_minutes,
        )

    @classmethod
    def _build_evidence_timeline(
        cls,
        incident: Incident,
        inv_dict: Dict[str, Any],
        metrics_summary: Optional[Dict[str, Any]],
        window_minutes: int,
    ) -> List[EvidenceItem]:
        raw_items: List[Tuple[datetime, EvidenceItem]] = []
        inc_id = incident.incident_id
        res_str = f"{incident.resource.kind.lower()}/{incident.resource.name}"
        ref_dt = parse_iso_time(incident.created_at or incident.last_seen)

        win_start = ref_dt - timedelta(minutes=window_minutes)
        win_end = ref_dt + timedelta(minutes=window_minutes)

        # A. Kubernetes Events
        events = inv_dict.get("events") or incident.evidence or []
        if isinstance(events, list):
            for ev in events:
                if isinstance(ev, dict):
                    ts_str = ev.get("last_timestamp") or ev.get("first_timestamp") or incident.last_seen or utc_now_iso()
                    ev_dt = parse_iso_time(ts_str)
                    ev_type = ev.get("type", "Warning")
                    reason = ev.get("reason", "Event")
                    msg = ev.get("message", "")
                    count = ev.get("count", 1)

                    count_str = f" (occurred {count}x)" if count > 1 else ""
                    obs = f"[{ev_type}] {reason}: {msg}{count_str}"
                    relevance = "HIGH" if ev_type == "Warning" or "fail" in reason.lower() else "MEDIUM"

                    raw_items.append((
                        ev_dt,
                        EvidenceItem(
                            evidence_id="",
                            incident_id=inc_id,
                            source="KUBERNETES_EVENT",
                            resource=res_str,
                            timestamp=ts_str,
                            signal_type=reason,
                            observation=obs,
                            relevance=relevance,
                            raw_reference={"event": ev},
                        )
                    ))

        # B. Container States & Reasons
        pod_info = inv_dict.get("pod") or {}
        containers = pod_info.get("containers", [])
        for c in containers:
            if isinstance(c, dict):
                c_name = c.get("name", "unknown")
                restarts = c.get("restart_count", 0)
                ready = c.get("ready", False)
                state_type = c.get("state_type", "unknown")
                reason = c.get("reason", "")
                msg = c.get("message", "")
                exit_code = c.get("exit_code")

                if restarts > 0:
                    raw_items.append((
                        ref_dt,
                        EvidenceItem(
                            evidence_id="",
                            incident_id=inc_id,
                            source="CONTAINER_STATE",
                            resource=f"container/{c_name}",
                            timestamp=incident.last_seen or utc_now_iso(),
                            signal_type="RestartCountIncrement",
                            observation=f"Container '{c_name}' in pod '{incident.resource.name}' has restarted {restarts} times.",
                            relevance="HIGH",
                        )
                    ))

                if state_type == "terminated" or exit_code is not None:
                    sig = reason or (f"ExitCode{exit_code}" if exit_code is not None else "Terminated")
                    code_str = f" (exit code {exit_code})" if exit_code is not None else ""
                    raw_items.append((
                        ref_dt,
                        EvidenceItem(
                            evidence_id="",
                            incident_id=inc_id,
                            source="CONTAINER_STATE",
                            resource=f"container/{c_name}",
                            timestamp=incident.last_seen or utc_now_iso(),
                            signal_type=sig,
                            observation=f"Container '{c_name}' terminated with reason '{reason or 'Unknown'}'{code_str}.",
                            relevance="HIGH",
                        )
                    ))

                elif state_type == "waiting" and reason:
                    raw_items.append((
                        ref_dt,
                        EvidenceItem(
                            evidence_id="",
                            incident_id=inc_id,
                            source="CONTAINER_STATE",
                            resource=f"container/{c_name}",
                            timestamp=incident.last_seen or utc_now_iso(),
                            signal_type=reason,
                            observation=f"Container '{c_name}' waiting with reason '{reason}': {msg or 'No message'}",
                            relevance="HIGH",
                        )
                    ))

        # C. Pod State & State Transitions
        pod_phase = pod_info.get("phase") or incident.current_state or "Unknown"
        raw_items.append((
            ref_dt,
            EvidenceItem(
                evidence_id="",
                incident_id=inc_id,
                source="POD_STATE",
                resource=res_str,
                timestamp=incident.last_seen or utc_now_iso(),
                signal_type="PodPhaseState",
                observation=f"Pod '{incident.resource.name}' current phase is '{pod_phase}' (Category: {incident.category}).",
                relevance="HIGH",
            )
        ))

        for idx, state_entry in enumerate(incident.state_history or []):
            st_name = state_entry if isinstance(state_entry, str) else str(state_entry.get("state", state_entry))
            raw_items.append((
                ref_dt - timedelta(seconds=len(incident.state_history) - idx),
                EvidenceItem(
                    evidence_id="",
                    incident_id=inc_id,
                    source="STATE_TRANSITION",
                    resource=res_str,
                    timestamp=incident.created_at or utc_now_iso(),
                    signal_type="StateShift",
                    observation=f"Incident state transition logged: {st_name}",
                    relevance="MEDIUM",
                )
            ))

        # D. Metrics Correlation
        if metrics_summary and metrics_summary.get("metrics_status") == "ONLINE":
            pods = metrics_summary.get("pods", [])
            target_pod = next((p for p in pods if p.get("name") == incident.resource.name and p.get("namespace") == incident.resource.namespace), None)
            if target_pod:
                cpu_m = target_pod.get("cpu_usage_mcores", 0.0)
                mem_mb = target_pod.get("memory_usage_mb", 0.0)

                if mem_mb > 100.0 or "OOM" in incident.category:
                    raw_items.append((
                        ref_dt,
                        EvidenceItem(
                            evidence_id="",
                            incident_id=inc_id,
                            source="METRIC",
                            resource=res_str,
                            timestamp=incident.last_seen or utc_now_iso(),
                            signal_type="PodMemoryUsageMetric",
                            observation=f"Pod real-time memory usage measured at {mem_mb:.1f} MB via metrics.k8s.io.",
                            relevance="HIGH",
                        )
                    ))
                if cpu_m > 50.0:
                    raw_items.append((
                        ref_dt,
                        EvidenceItem(
                            evidence_id="",
                            incident_id=inc_id,
                            source="METRIC",
                            resource=res_str,
                            timestamp=incident.last_seen or utc_now_iso(),
                            signal_type="PodCPUUsageMetric",
                            observation=f"Pod real-time CPU usage measured at {cpu_m:.1f} mCores via metrics.k8s.io.",
                            relevance="HIGH",
                        )
                    ))
        else:
            raw_items.append((
                ref_dt,
                EvidenceItem(
                    evidence_id="",
                    incident_id=inc_id,
                    source="METRIC",
                    resource=res_str,
                    timestamp=incident.last_seen or utc_now_iso(),
                    signal_type="MetricsUnavailable",
                    observation="Cluster resource metrics API (metrics.k8s.io) is unavailable or not reporting metrics for this workload.",
                    relevance="LOW",
                )
            ))

        # E. Logs Evidence (if present in investigation)
        recent_logs = inv_dict.get("recent_logs") or []
        for log_line in recent_logs[:5]:
            if isinstance(log_line, str) and log_line.strip():
                raw_items.append((
                    ref_dt,
                    EvidenceItem(
                        evidence_id="",
                        incident_id=inc_id,
                        source="LOG",
                        resource=res_str,
                        timestamp=incident.last_seen or utc_now_iso(),
                        signal_type="LogOutput",
                        observation=f"Container log output: {log_line[:200]}",
                        relevance="MEDIUM",
                    )
                ))

        # F. Node State Evidence
        node_info = inv_dict.get("node") or {}
        if isinstance(node_info, dict) and node_info.get("name"):
            n_name = node_info.get("name")
            n_status = node_info.get("status", "Ready")
            conds = node_info.get("conditions", {})
            if n_status != "Ready" or conds.get("MemoryPressure") == "True" or conds.get("DiskPressure") == "True":
                raw_items.append((
                    ref_dt,
                    EvidenceItem(
                        evidence_id="",
                        incident_id=inc_id,
                        source="NODE_STATE",
                        resource=f"node/{n_name}",
                        timestamp=incident.last_seen or utc_now_iso(),
                        signal_type="NodeConditionWarning",
                        observation=f"Node '{n_name}' status: {n_status}, conditions: {conds}",
                        relevance="HIGH",
                    )
                ))

        # Sort chronologically by timestamp
        raw_items.sort(key=lambda pair: pair[0])

        # Assign sequential evidence IDs
        final_timeline: List[EvidenceItem] = []
        for idx, (_, item) in enumerate(raw_items, 1):
            item.evidence_id = f"EVD-{idx:03d}"
            final_timeline.append(item)

        return final_timeline

    @classmethod
    def _evaluate_root_cause(
        cls,
        incident: Incident,
        inv_dict: Dict[str, Any],
        evidence_timeline: List[EvidenceItem],
    ) -> RootCauseAnalysis:
        category = (incident.category or "Unknown").upper()
        diag_dict = incident.diagnosis if isinstance(incident.diagnosis, dict) else {}
        candidate_cause = diag_dict.get("root_cause") or diag_dict.get("reason") or f"Resource failure: {incident.category}"

        # Deterministic Score Accumulator (0 - 100)
        score = 0
        score_breakdown: List[str] = []

        supporting: List[Dict[str, Any]] = []
        contradicting: List[Dict[str, Any]] = []

        # Check evidence signals
        has_exit_137 = False
        has_image_err = False
        has_backoff_event = False
        has_restarts = False
        has_node_issue = False
        has_probe_fail = False

        pod_info = inv_dict.get("pod") or {}
        containers = pod_info.get("containers", [])
        for c in containers:
            if isinstance(c, dict):
                exit_code = c.get("exit_code")
                reason = str(c.get("reason", "")).upper()
                restarts = c.get("restart_count", 0)

                if exit_code == 137 or "OOMKILLED" in reason:
                    has_exit_137 = True
                if "IMAGE" in reason or "ERRIMAGEPULL" in reason or "IMAGEPULLBACKOFF" in reason:
                    has_image_err = True
                if restarts > 0:
                    has_restarts = True

        for item in evidence_timeline:
            sig = item.signal_type.upper()
            obs = item.observation.upper()

            if "BACKOFF" in sig or "CRASH" in sig or "IMAGE" in sig:
                has_backoff_event = True
            if "NODE" in sig or "NODENOTREADY" in sig or "MEMORYPRESSURE" in sig:
                has_node_issue = True
            if "PROBE" in sig or "UNHEALTHY" in sig:
                has_probe_fail = True

            # Separate supporting vs contradicting
            if item.relevance in ("HIGH", "MEDIUM") and item.source != "METRIC":
                supporting.append(item.to_dict())

        # Category-Specific Scoring Rules
        if "OOM" in category or "OOMKILLED" in category:
            if has_exit_137:
                score += 35
                score_breakdown.append("Direct container exit code 137 / OOMKilled (+35)")
            else:
                score += 15
                score_breakdown.append("OOM failure category indicated (+15)")

        elif "IMAGE" in category or "ERRIMAGE" in category:
            if has_image_err or has_backoff_event:
                score += 35
                score_breakdown.append("Direct image pull failure / backoff event (+35)")
            else:
                score += 20
                score_breakdown.append("Image pull category indicated (+20)")

        elif "CRASH" in category or "BACKOFF" in category:
            if has_restarts:
                score += 30
                score_breakdown.append("Container restart count > 0 (+30)")
            if has_backoff_event:
                score += 20
                score_breakdown.append("BackOff warning events present (+20)")

        elif "PENDING" in category or "SCHEDUL" in category:
            score += 30
            score_breakdown.append("Unscheduled / Pending state confirmed (+30)")

        elif "NODE" in category:
            if has_node_issue:
                score += 35
                score_breakdown.append("Node condition NotReady / Pressure confirmed (+35)")
            else:
                score += 20
                score_breakdown.append("Node failure category indicated (+20)")

        else:
            score += 20
            score_breakdown.append("Resource failure pattern observed (+20)")

        # General supporting evidence multipliers
        warning_events_count = sum(1 for e in evidence_timeline if e.source == "KUBERNETES_EVENT" and "Warning" in e.observation)
        if warning_events_count > 0:
            add = min(25, warning_events_count * 10)
            score += add
            score_breakdown.append(f"Matching Kubernetes warning events found ({warning_events_count}x) (+{add})")

        if incident.occurrences > 1 or len(incident.state_history) > 1:
            score += 10
            score_breakdown.append("Multiple state transitions logged (+10)")

        # Check for contradicting evidence
        pod_phase = str(pod_info.get("phase", "")).upper()
        if pod_phase == "RUNNING":
            all_ready = all(c.get("ready", False) for c in containers if isinstance(c, dict))
            if all_ready and "CRASH" in category:
                score -= 25
                contradicting.append({
                    "statement": "Pod is currently in Running phase with all containers Ready",
                    "source": "pod.status"
                })
                score_breakdown.append("Contradiction: Pod is currently Running and Ready (-25)")

        # Clamp score between 0 and 100
        score = max(0, min(100, score))

        if score >= 80:
            level = "HIGH"
        elif score >= 50:
            level = "MEDIUM"
        else:
            level = "LOW"

        reasoning = f"Confidence score {score}% ({level}) calculated based on: {'; '.join(score_breakdown)}."

        # Derive recommended actions deterministically
        rec_actions = diag_dict.get("recommendations") or incident.recommendations or []
        if not rec_actions:
            rec_actions = [
                f"kubectl describe pod {incident.resource.name} -n {incident.resource.namespace}",
                f"kubectl logs {incident.resource.name} -n {incident.resource.namespace} --previous",
            ]

        return RootCauseAnalysis(
            candidate_root_cause=candidate_cause,
            confidence_score=score,
            confidence_level=level,
            confidence_reasoning=reasoning,
            supporting_evidence=supporting[:10],
            contradicting_evidence=contradicting,
            impacted_resources=[f"{incident.resource.kind.lower()}/{incident.resource.name}"],
            recommended_actions=rec_actions,
        )

    @classmethod
    def _calculate_blast_radius(
        cls,
        incident: Incident,
        inv_dict: Dict[str, Any],
    ) -> BlastRadius:
        ns = incident.resource.namespace
        pod_name = incident.resource.name

        impacted: List[Dict[str, Any]] = [
            {
                "kind": incident.resource.kind,
                "name": pod_name,
                "namespace": ns,
                "status": incident.current_state,
            }
        ]

        controllers = inv_dict.get("controllers") or []
        services = inv_dict.get("services") or []
        endpoints = inv_dict.get("endpoints") or []
        node_info = inv_dict.get("node") or {}

        workload_status: Dict[str, Any] = {}
        service_status: List[Dict[str, Any]] = []
        scope_level = "POD"

        # Check Controller Scope (Deployment / ReplicaSet / StatefulSet)
        controller_name = None
        controller_kind = None
        if isinstance(controllers, list) and controllers:
            ctrl = controllers[0]
            if isinstance(ctrl, dict):
                controller_name = ctrl.get("name")
                controller_kind = ctrl.get("kind", "Deployment")
                replicas = ctrl.get("replicas", 1)
                ready_replicas = ctrl.get("ready_replicas", 0)

                workload_status = {
                    "kind": controller_kind,
                    "name": controller_name,
                    "desired_replicas": replicas,
                    "ready_replicas": ready_replicas,
                    "affected_replicas": max(0, replicas - ready_replicas),
                }

                impacted.append({
                    "kind": controller_kind,
                    "name": controller_name,
                    "namespace": ns,
                    "status": "DEGRADED" if ready_replicas < replicas else "HEALTHY",
                })

                if replicas > 0 and ready_replicas < replicas:
                    scope_level = "WORKLOAD"

        # Check Service Scope
        if isinstance(services, list):
            for svc in services:
                if isinstance(svc, dict):
                    svc_name = svc.get("name")
                    ep_ready_count = 0
                    ep_total_count = 0

                    # Find matching endpoint
                    for ep in endpoints if isinstance(endpoints, list) else []:
                        if isinstance(ep, dict) and ep.get("name") == svc_name:
                            ep_ready_count = ep.get("ready_count", 0)
                            ep_total_count = ep.get("total_count", 0)

                    service_status.append({
                        "name": svc_name,
                        "namespace": ns,
                        "ready_endpoints": ep_ready_count,
                        "total_endpoints": ep_total_count,
                    })

                    impacted.append({
                        "kind": "Service",
                        "name": svc_name,
                        "namespace": ns,
                        "status": "DEGRADED" if ep_ready_count < ep_total_count else "HEALTHY",
                    })

        # Check Node Scope
        if isinstance(node_info, dict) and node_info.get("name"):
            n_name = node_info.get("name")
            n_status = node_info.get("status", "Ready")
            if n_status != "Ready":
                scope_level = "NODE"
                impacted.append({
                    "kind": "Node",
                    "name": n_name,
                    "namespace": "",
                    "status": n_status,
                })

        # Formulate human summary
        if scope_level == "WORKLOAD" and controller_name:
            aff = workload_status.get("affected_replicas", 1)
            tot = workload_status.get("desired_replicas", 1)
            summary = f"WORKLOAD scope: {aff} of {tot} replicas affected in {controller_kind} '{controller_name}' (namespace: '{ns}')."
        elif scope_level == "NODE":
            n_name = node_info.get("name", "unknown")
            summary = f"NODE scope: Node '{n_name}' is in degraded state ({node_info.get('status')}), impacting all pods on this node."
        else:
            summary = f"POD scope: Incident localized to individual pod '{pod_name}' in namespace '{ns}'."

        return BlastRadius(
            scope_level=scope_level,
            summary=summary,
            impacted_resources=impacted,
            workload_status=workload_status,
            service_status=service_status,
        )

    @classmethod
    def _find_related_incidents(
        cls,
        incident: Incident,
        existing_incidents: List[Incident],
    ) -> List[RelatedIncident]:
        related: List[RelatedIncident] = []
        target_id = incident.incident_id
        target_ns = incident.resource.namespace
        target_name = incident.resource.name
        target_uid = incident.resource.uid
        target_cat = incident.category

        for other in existing_incidents:
            if other.incident_id == target_id:
                continue

            rel_type = None
            if other.resource.namespace == target_ns and (other.resource.name == target_name or (other.resource.uid and other.resource.uid == target_uid)):
                rel_type = "SAME_RESOURCE"
            elif other.resource.namespace == target_ns:
                rel_type = "RELATED_RESOURCE"
            elif other.category == target_cat:
                rel_type = "SIMILAR_INCIDENT"

            if rel_type:
                related.append(RelatedIncident(
                    incident_id=other.incident_id,
                    resource_name=other.resource.name,
                    namespace=other.resource.namespace,
                    category=other.category,
                    relationship_type=rel_type,
                    created_at=other.created_at,
                    status=other.status,
                ))

        # Sort: SAME_RESOURCE first, then RELATED_RESOURCE, then SIMILAR_INCIDENT
        order_map = {"SAME_RESOURCE": 0, "RELATED_RESOURCE": 1, "SIMILAR_INCIDENT": 2}
        related.sort(key=lambda r: order_map.get(r.relationship_type, 3))

        return related[:10]
