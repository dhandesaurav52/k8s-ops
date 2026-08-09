# SkyOps Self-Hosted Unified Production Dockerfile
# Stage 1: Build React Web UI Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /build
COPY package*.json ./
RUN npm install
COPY . ./
RUN npm run build

# Stage 2: Unified Production Python Backend + React Static UI
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY cloud/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY cloud/app /app/cloud/app
COPY cloud/alembic /app/cloud/alembic
COPY cloud/alembic.ini /app/cloud/alembic.ini

# Copy compiled React UI build into container dist directory
COPY --from=frontend-builder /build/dist /app/dist

EXPOSE 8000

CMD ["uvicorn", "cloud.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

