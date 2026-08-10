from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator, root_validator


VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_STATUSES = {"OPEN", "RESOLVED"}


def _normalize_history_list(v: Any) -> List[Dict[str, Any]]:
    if not v:
        return []
    normalized = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for item in v:
        if isinstance(item, str):
            normalized.append({"state": item, "timestamp": now_iso, "reason": item})
        elif isinstance(item, dict):
            st = item.get("state") or item.get("reason") or "Unknown"
            rs = item.get("reason") or item.get("state") or "Unknown"
            ts = item.get("timestamp") or now_iso
            normalized.append({"state": st, "timestamp": ts, "reason": rs})
        else:
            s = str(item)
            normalized.append({"state": s, "timestamp": now_iso, "reason": s})
    return normalized


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

    @validator("state_history", pre=True, always=True)
    def validate_state_history(cls, v):
        return _normalize_history_list(v)

    @validator("severity", always=True)
    def validate_severity(cls, v):
        if v and v.upper() not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{v}'. Must be one of {VALID_SEVERITIES}")
        return v.upper() if v else "MEDIUM"

    @validator("status", always=True)
    def validate_status(cls, v):
        if v and v.upper() not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Must be one of {VALID_STATUSES}")
        return v.upper() if v else "OPEN"

    @root_validator(pre=False)
    def populate_resource_fields(cls, values):
        resource = values.get("resource")
        if resource:
            values["resource_kind"] = resource.kind
            values["resource_namespace"] = resource.namespace
            values["resource_name"] = resource.name
            values["resource_uid"] = resource.uid
        if not values.get("resource_name"):
            raise ValueError("resource_name or resource.name is required")
        return values


class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    current_state: Optional[str] = None
    severity: Optional[str] = None
    occurrences: Optional[int] = None
    diagnosis: Optional[Dict[str, Any]] = None
    investigation: Optional[Dict[str, Any]] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    state_history: Optional[List[Dict[str, Any]]] = None

    @validator("state_history", pre=True, always=True)
    def validate_state_history(cls, v):
        if v is None:
            return None
        return _normalize_history_list(v)

    @validator("severity")
    def validate_severity(cls, v):
        if v and v.upper() not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{v}'. Must be one of {VALID_SEVERITIES}")
        return v.upper() if v else None

    @validator("status")
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
    state_history: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    @validator("state_history", pre=True, always=True)
    def validate_state_history(cls, v):
        return _normalize_history_list(v)

    class Config:
        orm_mode = True
        from_attributes = True
