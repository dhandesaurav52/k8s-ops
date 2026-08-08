import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
import uvicorn

from cloud.app.api.clusters import router as clusters_router
from cloud.app.api.health import router as health_router
from cloud.app.api.incidents import router as incidents_router
from cloud.app.config import settings
from cloud.app.database import Base, engine

# Set up logging
logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("SkyOps.Cloud.Backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SkyOps Cloud Backend...")
    # Initialize database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema verified/created successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
    yield
    logger.info("Shutting down SkyOps Cloud Backend...")


app = FastAPI(
    title="SkyOps Cloud API",
    description="SkyOps Cloud Backend Service for multi-cluster incident management and agent telemetry.",
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

if __name__ == "__main__":
    uvicorn.run(
        "cloud.app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.SKYOPS_ENV == "development",
    )
