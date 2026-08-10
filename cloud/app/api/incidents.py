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
    dependencies=[Depends(get_current_identity)],
)


@router.get("", response_model=List[IncidentResponse], status_code=status.HTTP_200_OK)
def list_incidents(
    cluster_id: Optional[str] = Query(None, description="Filter incidents by cluster_id"),
    incident_status: Optional[str] = Query(None, alias="status", description="Filter by status (OPEN or RESOLVED)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List incidents with optional filtering."""
    return IncidentService.list_incidents(
        db, cluster_id=cluster_id, status=incident_status, skip=skip, limit=limit
    )


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(
    incident_in: IncidentCreate,
    db: Session = Depends(get_db),
):
    """Create or update an incident reported by an agent."""
    return IncidentService.create_or_upsert_incident(db, incident_in)


@router.get("/{incident_key}", response_model=IncidentResponse, status_code=status.HTTP_200_OK)
def get_incident(
    incident_key: str,
    cluster_id: Optional[str] = Query(None, description="Optional cluster_id if incident_key is string incident_id"),
    db: Session = Depends(get_db),
):
    """
    Retrieve incident by numeric database ID OR by incident_id (e.g. 'INC-0001').
    If incident_key is string incident_id, cluster_id query param can clarify scope.
    """
    incident = None
    if incident_key.isdigit():
        incident = IncidentService.get_incident(db, int(incident_key))

    if not incident and cluster_id:
        incident = IncidentService.get_incident_by_cluster_and_incident_id(
            db, cluster_id, incident_key
        )

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
    db: Session = Depends(get_db),
):
    """Update an incident by database ID."""
    existing = IncidentService.get_incident(db, id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {id} not found",
        )
    return IncidentService.update_incident(db, existing, incident_in)


@router.post("/{id}/resolve", response_model=IncidentResponse, status_code=status.HTTP_200_OK)
def resolve_incident(
    id: int,
    db: Session = Depends(get_db),
):
    """Mark an incident as RESOLVED."""
    existing = IncidentService.get_incident(db, id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {id} not found",
        )
    return IncidentService.resolve_incident(db, existing)
