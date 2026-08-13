import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from fastapi.middleware.cors import CORSMiddleware
from cloud.app.api.auth import router as auth_router
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
    os.makedirs("data", exist_ok=True)
    # Initialize database tables
    try:
        alembic_ini_path = os.path.join(os.getcwd(), "cloud", "alembic.ini")
        if not os.path.exists(alembic_ini_path):
            alembic_ini_path = os.path.join(os.getcwd(), "alembic.ini")

        if os.path.exists(alembic_ini_path):
            logger.info(f"Running Alembic migrations from {alembic_ini_path}...")
            from alembic.config import Config
            from alembic import command
            alembic_cfg = Config(alembic_ini_path)
            script_location = os.path.join(os.path.dirname(os.path.abspath(alembic_ini_path)), "alembic")
            alembic_cfg.set_main_option("script_location", script_location)
            command.upgrade(alembic_cfg, "head")
            logger.info("Alembic database migrations completed successfully.")
        else:
            Base.metadata.create_all(bind=engine)
            logger.info("Database schema verified/created successfully.")
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

# CORS Configuration
allowed_origins = [o.strip() for o in settings.SKYOPS_ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to every HTTP response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    err_msg = str(exc)
    # Redact potential credentials in exception string
    for secret in [settings.SKYOPS_AGENT_TOKEN, settings.SKYOPS_ADMIN_PASSWORD, settings.SKYOPS_SECRET_KEY]:
        if secret and secret in err_msg:
            err_msg = err_msg.replace(secret, "[REDACTED]")
    logger.error(f"Unhandled error handling request '{request.method} {request.url.path}': {err_msg}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


# Register API routers
app.include_router(health_router)
app.include_router(auth_router)
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
