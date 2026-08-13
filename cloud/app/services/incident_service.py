from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from cloud.app.models.cluster import Cluster
from cloud.app.models.incident import Incident
from cloud.app.schemas.incident import IncidentCreate, IncidentUpdate
from cloud.app.services.cluster_service import ClusterService


class IncidentService:
    @staticmethod
    def get_incident(db: Session, incident_db_id: int, organization_id: Optional[str] = None) -> Optional[Incident]:
        query = db.query(Incident).filter(Incident.id == incident_db_id)
        if organization_id:
            query = query.filter(Incident.organization_id == organization_id)
        return query.first()

    @staticmethod
    def get_incident_by_cluster_and_incident_id(
        db: Session, organization_id: str, cluster_id: str, incident_id: str
    ) -> Optional[Incident]:
        return (
            db.query(Incident)
            .filter(
                Incident.organization_id == organization_id,
                Incident.cluster_id == cluster_id,
                Incident.incident_id == incident_id,
            )
            .first()
        )

    @staticmethod
    def get_incident_by_incident_id(
        db: Session, organization_id: str, incident_id: str
    ) -> Optional[Incident]:
        return (
            db.query(Incident)
            .filter(
                Incident.organization_id == organization_id,
                Incident.incident_id == incident_id,
            )
            .order_by(Incident.created_at.desc())
            .first()
        )

    @staticmethod
    def list_incidents(
        db: Session,
        organization_id: str,
        cluster_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Incident]:
        query = db.query(Incident).filter(Incident.organization_id == organization_id)
        if cluster_id:
            query = query.filter(Incident.cluster_id == cluster_id)
        if status:
            query = query.filter(Incident.status == status.upper())
        return query.order_by(Incident.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def create_or_upsert_incident(
        db: Session, organization_id: str, data: IncidentCreate
    ) -> Incident:
        now = datetime.now(timezone.utc)

        # 1. Ensure Cluster exists and update heartbeat
        cluster = db.query(Cluster).filter(Cluster.cluster_id == data.cluster_id).first()
        if cluster:
            try:
                cluster.last_seen = now
                cluster.status = "CONNECTED"
                db.commit()
            except Exception:
                db.rollback()

        # Safely extract dicts/lists
        diagnosis_dict = data.diagnosis if isinstance(data.diagnosis, dict) else {}
        investigation_dict = data.investigation if isinstance(data.investigation, dict) else {}
        ai_analysis_dict = data.ai_analysis if isinstance(data.ai_analysis, dict) else {}
        history_list = data.state_history if isinstance(data.state_history, list) else []

        # 2. Check for existing incident by (organization_id, cluster_id, incident_id)
        existing = IncidentService.get_incident_by_cluster_and_incident_id(
            db, organization_id, data.cluster_id, data.incident_id
        )

        # 2b. Check for active OPEN incident on same resource_uid
        if not existing and data.resource_uid:
            existing = (
                db.query(Incident)
                .filter(
                    Incident.organization_id == organization_id,
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
            if diagnosis_dict:
                existing.diagnosis = diagnosis_dict
            if investigation_dict:
                existing.investigation = investigation_dict
            if ai_analysis_dict:
                existing.ai_analysis = ai_analysis_dict
            if history_list:
                existing.state_history = history_list
            existing.updated_at = now
            try:
                db.commit()
                db.refresh(existing)
                return existing
            except Exception:
                db.rollback()
                existing = IncidentService.get_incident_by_cluster_and_incident_id(
                    db, organization_id, data.cluster_id, data.incident_id
                )
                if existing:
                    return existing
                raise

        # Create new incident
        resolved_at = now if data.status == "RESOLVED" else None
        new_incident = Incident(
            organization_id=organization_id,
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
            diagnosis=diagnosis_dict,
            investigation=investigation_dict,
            ai_analysis=ai_analysis_dict,
            state_history=history_list,
            created_at=now,
            updated_at=now,
            resolved_at=resolved_at,
        )
        try:
            db.add(new_incident)
            db.commit()
            db.refresh(new_incident)
            return new_incident
        except IntegrityError:
            db.rollback()
            existing = IncidentService.get_incident_by_cluster_and_incident_id(
                db, organization_id, data.cluster_id, data.incident_id
            )
            if existing:
                return existing
            raise

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
