from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from cloud.app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    organization_id = Column(
        String(100),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    cluster_id = Column(
        String(100),
        ForeignKey("clusters.cluster_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    incident_id = Column(String(50), index=True, nullable=False)
    resource_kind = Column(String(50), default="Pod", nullable=False)
    resource_namespace = Column(String(100), default="default", nullable=False)
    resource_name = Column(String(255), nullable=False)
    resource_uid = Column(String(100), default="", nullable=False)
    category = Column(String(100), nullable=False)
    status = Column(String(20), default="OPEN", nullable=False)  # OPEN | INVESTIGATING | RESOLVED | ACKNOWLEDGED
    current_state = Column(Text, default="", nullable=False)
    severity = Column(String(20), default="MEDIUM", nullable=False)  # LOW | MEDIUM | HIGH | CRITICAL
    occurrences = Column(Integer, default=1, nullable=False)
    diagnosis = Column(JSON, default=dict, nullable=False)
    investigation = Column(JSON, default=dict, nullable=False)
    ai_analysis = Column(JSON, default=dict, nullable=False)
    state_history = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", back_populates="incidents")
    cluster = relationship("Cluster", back_populates="incidents")

    __table_args__ = (
        UniqueConstraint("cluster_id", "incident_id", name="uq_cluster_incident"),
    )
