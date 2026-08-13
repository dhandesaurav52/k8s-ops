from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from cloud.app.auth import get_current_identity
from cloud.app.database import get_db
from cloud.app.schemas.cluster import ClusterCreate, ClusterResponse, ClusterUpdate
from cloud.app.services.cluster_service import ClusterService

router = APIRouter(
    prefix="/api/v1/clusters",
    tags=["Clusters"],
)


@router.get("", response_model=List[ClusterResponse], status_code=status.HTTP_200_OK)
def list_clusters(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """List all registered clusters for caller's organization."""
    org_id = identity.get("organization_id", "org-default")
    return ClusterService.get_clusters(db, organization_id=org_id, skip=skip, limit=limit)


@router.post("", response_model=ClusterResponse, status_code=status.HTTP_201_CREATED)
def register_cluster(
    cluster_in: ClusterCreate,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Register or update cluster metadata from SkyOps agent heartbeat."""
    org_id = identity.get("organization_id", "org-default")
    cluster_id = identity.get("cluster_id") or cluster_in.cluster_id
    return ClusterService.register_or_update_cluster(
        db, organization_id=org_id, cluster_id=cluster_id, data=cluster_in
    )


@router.get("/{cluster_id}", response_model=ClusterResponse, status_code=status.HTTP_200_OK)
def get_cluster(
    cluster_id: str,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Retrieve cluster details by cluster_id."""
    org_id = identity.get("organization_id", "org-default")
    cluster = ClusterService.get_cluster(db, cluster_id, organization_id=org_id)
    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster '{cluster_id}' not found",
        )
    return cluster


@router.patch("/{cluster_id}", response_model=ClusterResponse, status_code=status.HTTP_200_OK)
def update_cluster(
    cluster_id: str,
    cluster_in: ClusterUpdate,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Update cluster metadata."""
    org_id = identity.get("organization_id", "org-default")
    updated = ClusterService.update_cluster(db, cluster_id, org_id, cluster_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster '{cluster_id}' not found",
        )
    return updated
