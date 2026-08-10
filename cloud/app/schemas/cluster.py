from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ClusterCreate(BaseModel):
    cluster_id: str = Field(..., min_length=1, description="Unique identifier for the cluster")
    name: Optional[str] = Field("unknown", description="Human-readable cluster name")
    kubernetes_version: Optional[str] = Field("unknown", description="K8s server version")
    status: Optional[str] = Field("CONNECTED", description="Connection status: CONNECTED or DISCONNECTED")
    node_count: Optional[int] = Field(0, ge=0)
    pod_count: Optional[int] = Field(0, ge=0)
    namespace_count: Optional[int] = Field(0, ge=0)


class ClusterUpdate(BaseModel):
    name: Optional[str] = None
    kubernetes_version: Optional[str] = None
    status: Optional[str] = None
    node_count: Optional[int] = Field(None, ge=0)
    pod_count: Optional[int] = Field(None, ge=0)
    namespace_count: Optional[int] = Field(None, ge=0)


class ClusterResponse(BaseModel):
    id: int
    cluster_id: str
    name: str
    kubernetes_version: str
    status: str
    node_count: int
    pod_count: int
    namespace_count: int
    last_seen: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True
