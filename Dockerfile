# SkyOps Kubernetes Cluster Agent Dockerfile
FROM python:3.11-slim

# Prevent Python from writing bytecode and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install dependencies first for efficient layer caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app /app/app
COPY main.py /app/main.py

# Create data directory and non-root user
RUN mkdir -p /app/data && \
    groupadd -g 10001 skyops && \
    useradd -u 10001 -g skyops -s /bin/bash -m skyops && \
    chown -R skyops:skyops /app

USER 10001:10001

EXPOSE 8080

CMD ["python", "-m", "app.agent.main"]
