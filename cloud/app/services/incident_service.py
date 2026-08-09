from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from cloud.app.models.cluster import Cluster
from cloud.app.models.incident import Incident
from cloud.app.schemas.incident import IncidentCreate, IncidentUpdate
from cloud.app.services.cluster_service import ClusterService


class IncidentService:
    @staticmethod
    def get_incident(db: Session, incident_db_id: int) -> Optional[Incident]:
        return db.query(Incident).filter(Incident.id == incident_db_id).first()

    @staticmethod
    def get_incident_by_cluster_and_incident_id(
        db: Session, cluster_id: str, incident_id: str
    ) -> Optional[Incident]:
        return (
            db.query(Incident)
            .filter(Incident.cluster_id == cluster_id, Incident.incident_id == incident_id)
            .first()
        )

    @staticmethod
    def list_incidents(
        db: Session,
        cluster_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Incident]:
        query = db.query(Incident)
        if cluster_id:
            query = query.filter(Incident.cluster_id == cluster_id)
        if status:
            query = query.filter(Incident.status == status.upper())
        return query.order_by(Incident.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def create_or_upsert_incident(db: Session, data: IncidentCreate) -> Incident:
        now = datetime.now(timezone.utc)

        # 1. Ensure Cluster exists
        cluster = ClusterService.get_cluster(db, data.cluster_id)
        if not cluster:
            # Auto-register cluster stub
            cluster = Cluster(
                cluster_id=data.cluster_id,
                name="unknown",
                kubernetes_version="unknown",
                status="CONNECTED",
                last_seen=now,
                created_at=now,
                updated_at=now,
            )
            db.add(cluster)
            db.commit()
            db.refresh(cluster)

        # 2. Check for existing incident by (cluster_id, incident_id)
        existing = IncidentService.get_incident_by_cluster_and_incident_id(
            db, data.cluster_id, data.incident_id
        )

        # 2b. If not found by incident_id, check for active OPEN incident on same resource_uid
        if not existing and data.resource_uid:
            existing = (
                db.query(Incident)
                .filter(
                    Incident.cluster_id == data.cluster_id,
                    Incident.resource_uid == data.resource_uid,
                    Incident.status == "OPEN",
                )
                .first()
            )

        if existing:
            # Update existing
            existing.category = data.category
            existing.current_state = data.current_state or existing.current_state
            existing.severity = data.severity or existing.severity
            existing.occurrences = data.occurrences or existing.occurrences
            if data.status:
                existing.status = data.status
                if data.status == "RESOLVED" and not existing.resolved_at:
                    existing.resolved_at = now
            if data.diagnosis:
                existing.diagnosis = data.diagnosis
            if data.investigation:
                existing.investigation = data.investigation
            if data.ai_analysis:
                existing.ai_analysis = data.ai_analysis
            if data.state_history:
                existing.state_history = data.state_history
            existing.updated_at = now
            db.commit()
            db.refresh(existing)
            return existing

        # Create new incident
        resolved_at = now if data.status == "RESOLVED" else None
        new_incident = Incident(
            cluster_id=data.cluster_id,
            incident_id=data.incident_id,
            resource_kind=data.resource_kind or "Pod",
            resource_namespace=data.resource_namespace or "default",
            resource_name=data.resource_name,
            resource_uid=data.resource_uid or "",
            category=data.category,
            status=data.status or "OPEN",
            current_state=data.current_state or "",
            severity=data.severity or "MEDIUM",
            occurrences=data.occurrences or 1,
            diagnosis=data.diagnosis or {},
            investigation=data.investigation or {},
            ai_analysis=data.ai_analysis or {},
            state_history=data.state_history or [],
            created_at=now,
            updated_at=now,
            resolved_at=resolved_at,
        )
        db.add(new_incident)
        db.commit()
        db.refresh(new_incident)
        return new_incident

    @staticmethod
    def update_incident(
        db: Session, incident_obj: Incident, data: IncidentUpdate
    ) -> Incident:
        now = datetime.now(timezone.utc)
        update_dict = data.model_dump(exclude_unset=True)

        for key, value in update_dict.items():
            if value is not None:
                setattr(incident_obj, key, value)

        if data.status == "RESOLVED" and not incident_obj.resolved_at:
            incident_obj.resolved_at = now
        elif data.status == "OPEN":
            incident_obj.resolved_at = None

        incident_obj.updated_at = now
        db.commit()
        db.refresh(incident_obj)
        return incident_obj

    @staticmethod
    def resolve_incident(db: Session, incident_obj: Incident) -> Incident:
        now = datetime.now(timezone.utc)
        incident_obj.status = "RESOLVED"
        incident_obj.resolved_at = now
        incident_obj.updated_at = now
        db.commit()
        db.refresh(incident_obj)
        return incident_obj
