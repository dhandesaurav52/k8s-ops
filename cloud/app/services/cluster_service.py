from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from cloud.app.models.cluster import Cluster
from cloud.app.schemas.cluster import ClusterCreate, ClusterUpdate


class ClusterService:
    @staticmethod
    def get_cluster(db: Session, cluster_id: str) -> Optional[Cluster]:
        return db.query(Cluster).filter(Cluster.cluster_id == cluster_id).first()

    @staticmethod
    def get_clusters(db: Session, skip: int = 0, limit: int = 100) -> List[Cluster]:
        return db.query(Cluster).offset(skip).limit(limit).all()

    @staticmethod
    def register_or_update_cluster(db: Session, data: ClusterCreate) -> Cluster:
        existing = db.query(Cluster).filter(Cluster.cluster_id == data.cluster_id).first()
        now = datetime.now(timezone.utc)
        if existing:
            if data.name and data.name != "unknown":
                existing.name = data.name
            if data.kubernetes_version and data.kubernetes_version != "unknown":
                existing.kubernetes_version = data.kubernetes_version
            if data.status:
                existing.status = data.status
            if data.node_count is not None:
                existing.node_count = data.node_count
            if data.pod_count is not None:
                existing.pod_count = data.pod_count
            if data.namespace_count is not None:
                existing.namespace_count = data.namespace_count
            existing.last_seen = now
            existing.updated_at = now
            db.commit()
            db.refresh(existing)
            return existing

        new_cluster = Cluster(
            cluster_id=data.cluster_id,
            name=data.name or "unknown",
            kubernetes_version=data.kubernetes_version or "unknown",
            status=data.status or "CONNECTED",
            node_count=data.node_count or 0,
            pod_count=data.pod_count or 0,
            namespace_count=data.namespace_count or 0,
            last_seen=now,
            created_at=now,
            updated_at=now,
        )
        db.add(new_cluster)
        db.commit()
        db.refresh(new_cluster)
        return new_cluster

    @staticmethod
    def update_cluster(db: Session, cluster_id: str, data: ClusterUpdate) -> Optional[Cluster]:
        cluster = ClusterService.get_cluster(db, cluster_id)
        if not cluster:
            return None
        now = datetime.now(timezone.utc)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(cluster, key, value)
        cluster.updated_at = now
        cluster.last_seen = now
        db.commit()
        db.refresh(cluster)
        return cluster
