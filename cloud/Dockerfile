# SkyOps Server Backend Dockerfile
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

EXPOSE 8000

CMD ["uvicorn", "cloud.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
