from fastapi import APIRouter, Response, status
from cloud.app.database import check_db_connection

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Basic health probe."""
    return {"status": "healthy"}


@router.get("/ready")
def readiness_check(response: Response):
    """Database readiness probe."""
    is_ready = check_db_connection()
    if is_ready:
        return {"status": "ready", "database": "connected"}
    
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "not_ready", "database": "disconnected"}
