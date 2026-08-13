import uuid
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from cloud.app.models.cluster import Cluster
from cloud.app.schemas.cluster import ClusterCreate, ClusterUpdate
from cloud.app.auth import generate_agent_token


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


class ClusterService:
    @staticmethod
    def get_cluster(db: Session, cluster_id: str, organization_id: Optional[str] = None) -> Optional[Cluster]:
        query = db.query(Cluster).filter(Cluster.cluster_id == cluster_id)
        if organization_id:
            query = query.filter(Cluster.organization_id == organization_id)
        return query.first()

    @staticmethod
    def get_clusters(db: Session, organization_id: str, skip: int = 0, limit: int = 100) -> List[Cluster]:
        return (
            db.query(Cluster)
            .filter(Cluster.organization_id == organization_id)
            .order_by(Cluster.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def onboard_cluster(db: Session, organization_id: str, name: str, server_url: str = "https://api.skyops.io") -> Dict[str, Any]:
        """Onboard a new cluster for an organization and generate secure registration Helm command."""
        slug_name = slugify(name) or "cluster"
        short_id = uuid.uuid4().hex[:6]
        cluster_id = f"{slug_name}-{short_id}"
        agent_token = generate_agent_token()
        now = datetime.now(timezone.utc)

        cluster = Cluster(
            organization_id=organization_id,
            cluster_id=cluster_id,
            name=name,
            agent_token=agent_token,
            kubernetes_version="unknown",
            status="DISCONNECTED",
            node_count=0,
            pod_count=0,
            namespace_count=0,
            last_seen=now,
            created_at=now,
            updated_at=now,
        )
        db.add(cluster)
        db.commit()
        db.refresh(cluster)

        clean_server_url = server_url.rstrip("/")
        helm_cmd = (
            f"helm repo add skyops https://dhandesaurav52.github.io/k8s-ops\n"
            f"helm repo update\n\n"
            f"helm install skyops-agent skyops/agent \\\n"
            f"  --namespace skyops-system \\\n"
            f"  --create-namespace \\\n"
            f"  --set server.url={clean_server_url} \\\n"
            f"  --set cluster.name={cluster.name} \\\n"
            f"  --set agent.token={agent_token}"
        )

        return {
            "cluster_id": cluster.cluster_id,
            "name": cluster.name,
            "agent_token": agent_token,
            "helm_command": helm_cmd,
        }

    @staticmethod
    def register_or_update_cluster(db: Session, organization_id: str, cluster_id: str, data: ClusterCreate) -> Cluster:
        now = datetime.now(timezone.utc)
        existing = db.query(Cluster).filter(Cluster.cluster_id == cluster_id).first()
        
        if not existing:
            # Look up by token or create new under tenant
            existing = db.query(Cluster).filter(
                Cluster.organization_id == organization_id,
                Cluster.name == data.name
            ).first()

        if existing:
            if data.name and data.name != "unknown":
                existing.name = data.name
            if data.kubernetes_version and data.kubernetes_version != "unknown":
                existing.kubernetes_version = data.kubernetes_version
            existing.status = "CONNECTED"
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

        # Create new cluster record
        token = generate_agent_token()
        new_cluster = Cluster(
            organization_id=organization_id,
            cluster_id=cluster_id,
            name=data.name or "unknown",
            agent_token=token,
            kubernetes_version=data.kubernetes_version or "unknown",
            status="CONNECTED",
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
    def update_cluster(db: Session, cluster_id: str, organization_id: str, data: ClusterUpdate) -> Optional[Cluster]:
        cluster = ClusterService.get_cluster(db, cluster_id, organization_id=organization_id)
        if not cluster:
            return None
        now = datetime.now(timezone.utc)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(cluster, key, value)
        cluster.updated_at = now
        db.commit()
        db.refresh(cluster)
        return cluster
