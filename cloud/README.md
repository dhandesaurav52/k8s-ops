# SkyOps Cloud Backend Foundation (Phase 5)

SkyOps Cloud Backend is a FastAPI service with PostgreSQL for receiving, managing, and indexing multi-cluster Kubernetes agent data and incident telemetry.

## Features

- **Health & Readiness Endpoints**: `/health` and `/ready` with database status verification
- **Cluster Registry API**: `/api/v1/clusters` for registering and tracking Kubernetes cluster metadata
- **Incident API**: `/api/v1/incidents` for incident ingestion, status updates, and lifecycle resolution
- **Incident Deduplication**: Unique constraint enforcement on `(cluster_id, incident_id)`
- **Multi-Cluster Isolation**: Same `incident_id` across different clusters are tracked independently
- **Alembic Database Migrations**: Automated schema versioning for PostgreSQL

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://skyops:password@localhost:5432/skyops` | PostgreSQL connection string |
| `SKYOPS_ENV` | `development` | Deployment environment |
| `LOG_LEVEL` | `INFO` | Logging verbosity level |
| `API_HOST` | `0.0.0.0` | API listen host |
| `API_PORT` | `8000` | API listen port |

## Quickstart

### Local Development (with Docker Compose)

```bash
docker-compose up -d --build
```

### Database Migrations

```bash
cd cloud
alembic upgrade head
```

### Running Tests

```bash
pytest cloud/tests
```

### API Documentation

Interactive OpenAPI documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
