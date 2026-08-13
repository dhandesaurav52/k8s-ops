from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from cloud.app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    organization_id = Column(
        String(100),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    cluster_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(100), default="unknown", nullable=False)
    agent_token = Column(String(255), unique=True, index=True, nullable=False)
    kubernetes_version = Column(String(50), default="unknown", nullable=False)
    status = Column(String(20), default="DISCONNECTED", nullable=False)  # CONNECTED | DISCONNECTED | PENDING
    node_count = Column(Integer, default=0, nullable=False)
    pod_count = Column(Integer, default=0, nullable=False)
    namespace_count = Column(Integer, default=0, nullable=False)
    last_seen = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    organization = relationship("Organization", back_populates="clusters")
    incidents = relationship("Incident", back_populates="cluster", cascade="all, delete-orphan")
