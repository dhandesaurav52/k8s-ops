import uuid
import re
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from cloud.app.auth import get_current_identity
from cloud.app.database import get_db
from cloud.app.models.organization import Organization, Membership
from cloud.app.schemas.organization import OrganizationCreate, OrganizationResponse, ClusterOnboardResponse
from cloud.app.services.cluster_service import ClusterService

router = APIRouter(
    prefix="/api/v1/organizations",
    tags=["Organizations"],
)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


@router.get("", response_model=List[OrganizationResponse], status_code=status.HTTP_200_OK)
def list_organizations(
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """List organizations for current identity."""
    org_id = identity.get("organization_id")
    if org_id:
        orgs = db.query(Organization).filter(Organization.org_id == org_id).all()
        if orgs:
            return orgs
    return db.query(Organization).all()


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    org_in: OrganizationCreate,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Create a new organization."""
    slug = slugify(org_in.name) or "org"
    short_id = uuid.uuid4().hex[:6]
    org_id = f"org-{slug}-{short_id}"

    org = Organization(
        org_id=org_id,
        name=org_in.name,
        slug=f"{slug}-{short_id}",
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.post("/clusters/onboard", response_model=ClusterOnboardResponse, status_code=status.HTTP_201_CREATED)
def onboard_cluster(
    cluster_name: str = Query(..., description="Name of cluster to onboard"),
    request: Request = None,
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Generate agent registration token and Helm command to onboard a new Kubernetes cluster."""
    org_id = identity.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Missing organization context")

    host = request.headers.get("host", "api.skyops.io") if request else "api.skyops.io"
    scheme = "https" if "https" in request.headers.get("x-forwarded-proto", "") or "run.app" in host else "http"
    server_url = f"{scheme}://{host}"

    return ClusterService.onboard_cluster(db, organization_id=org_id, name=cluster_name, server_url=server_url)
