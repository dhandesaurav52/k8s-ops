import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from cloud.app.api.clusters import router as clusters_router
from cloud.app.api.health import router as health_router
from cloud.app.api.incidents import router as incidents_router
from cloud.app.api.metrics import router as metrics_router
from cloud.app.api.remediations import router as remediations_router
from cloud.app.config import settings
from cloud.app.database import Base, engine, SessionLocal
from cloud.app.services.cluster_service import ClusterService
from cloud.app.schemas.cluster import ClusterCreate

# Set up logging
logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("SkyOps.Server.Backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SkyOps Server Backend...")
    # Initialize database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema verified/created successfully.")
        
        # Ensure default seed cluster exists if DB is fresh
        db = SessionLocal()
        try:
            clusters = ClusterService.get_clusters(db)
            if not clusters:
                logger.info("Seeding initial cluster in PostgreSQL...")
                ClusterService.register_or_update_cluster(
                    db,
                    ClusterCreate(
                        cluster_id="skyops-cluster-prod-us",
                        name="prod-us-east-1a",
                        status="CONNECTED",
                        kubernetes_version="v1.28.4-gke",
                        node_count=8,
                        pod_count=142,
                        namespace_count=12,
                    )
                )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
    yield
    logger.info("Shutting down SkyOps Server Backend...")


app = FastAPI(
    title="SkyOps Server API",
    description="SkyOps Server Backend Service for multi-cluster incident management and agent telemetry.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error handling request '{request.method} {request.url.path}': {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


# Register API routers
app.include_router(health_router)
app.include_router(clusters_router)
app.include_router(incidents_router)
app.include_router(metrics_router)
app.include_router(remediations_router)

# Static file serving for React Web UI (production dist/ directory)
dist_path = os.path.join(os.getcwd(), "dist")
if os.path.exists(dist_path):
    assets_path = os.path.join(dist_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if (
            full_path.startswith("api/")
            or full_path.startswith("docs")
            or full_path.startswith("redoc")
            or full_path.startswith("openapi.json")
            or full_path.startswith("health")
            or full_path.startswith("ready")
        ):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        target_file = os.path.join(dist_path, full_path)
        if os.path.exists(target_file) and os.path.isfile(target_file):
            return FileResponse(target_file)
        index_file = os.path.join(dist_path, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return JSONResponse(status_code=404, content={"detail": "Web UI index.html not found"})


if __name__ == "__main__":
    uvicorn.run(
        "cloud.app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.SKYOPS_ENV == "development",
    )
