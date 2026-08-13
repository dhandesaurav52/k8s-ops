from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from cloud.app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    organization_id = Column(
        String(100),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    cluster_id = Column(String(100), index=True, nullable=True)
    actor = Column(String(100), nullable=False, default="system")
    action = Column(String(100), nullable=False)
    details = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
