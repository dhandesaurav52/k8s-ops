from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_STATUSES = {"OPEN", "RESOLVED"}


class ResourceSchema(BaseModel):
    kind: str = "Pod"
    namespace: str = "default"
    name: str
    uid: str = ""


class IncidentCreate(BaseModel):
    cluster_id: str = Field(..., min_length=1)
    incident_id: str = Field(..., min_length=1)
    resource: Optional[ResourceSchema] = None
    resource_kind: Optional[str] = "Pod"
    resource_namespace: Optional[str] = "default"
    resource_name: Optional[str] = None
    resource_uid: Optional[str] = ""
    category: str = Field(..., min_length=1)
    status: Optional[str] = "OPEN"
    current_state: Optional[str] = ""
    severity: Optional[str] = "MEDIUM"
    occurrences: Optional[int] = 1
    diagnosis: Optional[Dict[str, Any]] = Field(default_factory=dict)
    investigation: Optional[Dict[str, Any]] = Field(default_factory=dict)
    ai_analysis: Optional[Dict[str, Any]] = Field(default_factory=dict)
    state_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v):
        if v and v.upper() not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{v}'. Must be one of {VALID_SEVERITIES}")
        return v.upper() if v else "MEDIUM"

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v and v.upper() not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Must be one of {VALID_STATUSES}")
        return v.upper() if v else "OPEN"

    @model_validator(mode="after")
    def populate_resource_fields(self):
        if self.resource:
            self.resource_kind = self.resource.kind
            self.resource_namespace = self.resource.namespace
            self.resource_name = self.resource.name
            self.resource_uid = self.resource.uid
        if not self.resource_name:
            raise ValueError("resource_name or resource.name is required")
        return self


class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    current_state: Optional[str] = None
    severity: Optional[str] = None
    occurrences: Optional[int] = None
    diagnosis: Optional[Dict[str, Any]] = None
    investigation: Optional[Dict[str, Any]] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    state_history: Optional[List[Dict[str, Any]]] = None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v):
        if v and v.upper() not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{v}'. Must be one of {VALID_SEVERITIES}")
        return v.upper() if v else None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v and v.upper() not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Must be one of {VALID_STATUSES}")
        return v.upper() if v else None


class IncidentResponse(BaseModel):
    id: int
    cluster_id: str
    incident_id: str
    resource_kind: str
    resource_namespace: str
    resource_name: str
    resource_uid: str
    category: str
    status: str
    current_state: str
    severity: str
    occurrences: int
    diagnosis: Dict[str, Any]
    investigation: Dict[str, Any]
    ai_analysis: Dict[str, Any]
    state_history: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
