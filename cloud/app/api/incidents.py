from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from cloud.app.auth import get_current_identity
from cloud.app.database import get_db
from cloud.app.schemas.incident import IncidentCreate, IncidentResponse, IncidentUpdate
from cloud.app.services.incident_service import IncidentService

router = APIRouter(
    prefix="/api/v1/incidents",
    tags=["Incidents"],
)


@router.get("", response_model=List[IncidentResponse], status_code=status.HTTP_200_OK)
def list_incidents(
    cluster_id: Optional[str] = Query(None, description="Filter incidents by cluster_id"),
    incident_status: Optional[str] = Query(None, alias="status", description="Filter by status (OPEN or RESOLVED)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """List incidents with optional filtering for caller's organization."""
    org_id = identity.get("organization_id", "org-default")
    return IncidentService.list_incidents(
        db, organization_id=org_id, cluster_id=cluster_id, status=incident_status, skip=skip, limit=limit
    )


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(
    incident_in: IncidentCreate,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Create or update an incident reported by an agent."""
    org_id = identity.get("organization_id", "org-default")
    return IncidentService.create_or_upsert_incident(db, org_id, incident_in)


@router.get("/{incident_key}", response_model=IncidentResponse, status_code=status.HTTP_200_OK)
def get_incident(
    incident_key: str,
    cluster_id: Optional[str] = Query(None, description="Optional cluster_id if incident_key is string incident_id"),
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Retrieve incident by database ID or incident_id."""
    org_id = identity.get("organization_id", "org-default")
    incident = None
    if incident_key.isdigit():
        incident = IncidentService.get_incident(db, int(incident_key), organization_id=org_id)

    if not incident and cluster_id:
        incident = IncidentService.get_incident_by_cluster_and_incident_id(
            db, org_id, cluster_id, incident_key
        )

    if not incident and not incident_key.isdigit():
        incident = IncidentService.get_incident_by_incident_id(db, org_id, incident_key)

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_key}' not found",
        )
    return incident


@router.patch("/{id}", response_model=IncidentResponse, status_code=status.HTTP_200_OK)
def update_incident(
    id: int,
    incident_in: IncidentUpdate,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Update an incident by database ID."""
    org_id = identity.get("organization_id", "org-default")
    existing = IncidentService.get_incident(db, id, organization_id=org_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {id} not found",
        )
    return IncidentService.update_incident(db, existing, incident_in)


@router.post("/{id}/resolve", response_model=IncidentResponse, status_code=status.HTTP_200_OK)
def resolve_incident(
    id: int,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Mark an incident as RESOLVED."""
    org_id = identity.get("organization_id", "org-default")
    existing = IncidentService.get_incident(db, id, organization_id=org_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {id} not found",
        )
    return IncidentService.resolve_incident(db, existing)
