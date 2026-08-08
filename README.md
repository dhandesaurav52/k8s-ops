# SkyOps — Kubernetes Incident Detection & Investigation Platform

SkyOps is an automated Kubernetes incident detection, investigation, and lifecycle tracking engine.

## Phase 1 Architecture

```text
Kubernetes Cluster
       │
       ▼
SkyOps Watcher (K8s Watch API stream listener)
       │
       ▼
Incident Manager (Health evaluation, deduplication, identity key computation)
       │
       ▼
Diagnosis Engine (Deterministic root-cause, severity & recommendations)
       │
       ▼
JSON IncidentStore (Atomic data persistence to data/incidents.json)
```

## Features in Phase 1

- **Continuous Kubernetes Watcher**: Streams pod events via official Kubernetes Python SDK (`watch.Watch().stream()`).
- **Resilient Reconnection**: Automatically handles API timeouts, network interruptions, and transient cluster errors without crashing.
- **Stable Incident Identity & Deduplication**: Groups related failure state shifts (e.g. `ErrImagePull` -> `ImagePullBackOff`) for the same pod resource UID under a single incident ID (e.g., `INC-0001`).
- **Automatic Recovery Detection**: Monitors when unhealthy pods transition back to `Running` and `Ready`, transitioning the incident status from `OPEN` to `RESOLVED` while preserving full history.
- **Deterministic Diagnosis Engine**: Provides root causes and actionable recommendations for `ImagePullBackOff`, `CrashLoopBackOff`, `OOMKilled`, `ContainerConfigError`, `PodPending`, etc.
- **Zero Secret Exposure**: Strictly filters out `Secret.data` and tokens from all logs and incident evidence.
- **Atomic Local Storage**: Persists state to `data/incidents.json` using atomic temporary file writes.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run SkyOps Watcher
To run against an active Kubernetes cluster (configured via `~/.kube/config` or in-cluster service account):
```bash
python main.py
```

To run SkyOps in simulation mode (verifies complete incident lifecycle without needing a live cluster):
```bash
python main.py --simulate
```

### 3. Run Automated Test Suite
```bash
pytest
```
