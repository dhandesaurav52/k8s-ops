from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Organization name")


class OrganizationResponse(BaseModel):
    id: int
    org_id: str
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClusterOnboardResponse(BaseModel):
    cluster_id: str
    name: str
    agent_token: str
    helm_command: str
