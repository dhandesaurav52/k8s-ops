from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from cloud.app.database import get_db
from cloud.app.schemas.cluster import ClusterCreate, ClusterResponse, ClusterUpdate
from cloud.app.services.cluster_service import ClusterService

router = APIRouter(prefix="/api/v1/clusters", tags=["Clusters"])


@router.get("", response_model=List[ClusterResponse], status_code=status.HTTP_200_OK)
def list_clusters(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List all registered clusters."""
    return ClusterService.get_clusters(db, skip=skip, limit=limit)


@router.post("", response_model=ClusterResponse, status_code=status.HTTP_201_CREATED)
def register_cluster(
    cluster_in: ClusterCreate,
    db: Session = Depends(get_db),
):
    """Register or update cluster metadata."""
    return ClusterService.register_or_update_cluster(db, cluster_in)


@router.get("/{cluster_id}", response_model=ClusterResponse, status_code=status.HTTP_200_OK)
def get_cluster(
    cluster_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve cluster details by cluster_id."""
    cluster = ClusterService.get_cluster(db, cluster_id)
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
    db: Session = Depends(get_db),
):
    """Update cluster metadata."""
    updated = ClusterService.update_cluster(db, cluster_id, cluster_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster '{cluster_id}' not found",
        )
    return updated
