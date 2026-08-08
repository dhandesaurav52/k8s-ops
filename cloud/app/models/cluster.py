from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from cloud.app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cluster_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(100), default="unknown", nullable=False)
    kubernetes_version = Column(String(50), default="unknown", nullable=False)
    status = Column(String(20), default="CONNECTED", nullable=False)  # CONNECTED | DISCONNECTED
    node_count = Column(Integer, default=0, nullable=False)
    pod_count = Column(Integer, default=0, nullable=False)
    namespace_count = Column(Integer, default=0, nullable=False)
    last_seen = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    incidents = relationship("Incident", back_populates="cluster", cascade="all, delete-orphan")
