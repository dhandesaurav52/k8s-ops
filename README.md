# SkyOps — Self-Hosted Kubernetes Operations Platform

SkyOps is an enterprise-grade, self-hosted, Jenkins-style Kubernetes Observability, Root Cause Analysis & Safe Automated Remediation Platform. The customer owns the server, Web UI, API, database, and telemetry data.

---

## 1. Target Architecture

```text
                  CUSTOMER INFRASTRUCTURE / SERVER
       ┌──────────────────────────────────────────────────┐
       │                  SKYOPS SERVER                   │
       │                                                  │
       │  • React Web Console                             │
       │  • REST API                                      │
       │  • Incident & Investigation Engine               │
       │  • Gemini AI Root Cause Diagnosis                │
       │  • Metrics Aggregator                            │
       │  • Safe Automated Remediation Engine             │
       │  • Persistent Database & Audit Trail             │
       └────────────────────────┬─────────────────────────┘
                                │
                              HTTPS
                                │
             ┌──────────────────┼──────────────────┐
             │                  │                  │
             ▼                  ▼                  ▼
         Cluster A          Cluster B          Cluster C
             │                  │                  │
        SkyOps Agent       SkyOps Agent       SkyOps Agent
             │                  │                  │
         Kubernetes         Kubernetes         Kubernetes
```

---

## 2. Installation Guide

### Option A: Installing SkyOps Server (On Customer Server / VM)

Run SkyOps Server via Docker Compose:

```bash
cd cloud
docker compose up -d
```

Access the **SkyOps Web Console** at `http://<YOUR_SERVER_IP>:3000` (or `http://localhost:3000`).

---

### Option B: Installing SkyOps Agent (Inside Customer Kubernetes Cluster)

Deploy the SkyOps Agent into your Kubernetes cluster using the official published image (`dhandesaurav52/skyops-agent:0.1.0`):

```bash
# 1. Create skyops namespace
kubectl apply -f deploy/namespace.yaml

# 2. Configure ServiceAccount and RBAC permissions
kubectl apply -f deploy/serviceaccount.yaml
kubectl apply -f deploy/clusterrole.yaml
kubectl apply -f deploy/clusterrolebinding.yaml

# 3. Deploy SkyOps Agent
kubectl apply -f deploy/deployment.yaml
```

---

## 3. Incident & Remediation Lifecycle Workflow

```text
DETECTED ──► INVESTIGATED ──► AI DIAGNOSIS ──► DRY RUN VALIDATION ──► HUMAN APPROVAL ──► SAFE EXECUTION ──► VERIFICATION ──► RESOLVED
```

1. **Detection**: Agent captures pod/workload failure events (`OOMKilled`, `CrashLoopBackOff`, `ImagePullBackOff`).
2. **Investigation**: Agent gathers pod status, events, controller spec, node state, and container logs without leaking secrets.
3. **AI Diagnosis**: Gemini AI analyzes evidence to determine exact root cause and actionable fix.
4. **Dry Run**: Validates policy compliance and target resource existence without mutating cluster state.
5. **Human Approval**: SRE operator reviews proposed command and grants approval.
6. **Execution**: Safe execution of allowlisted Kubernetes actions (`RESOURCE_ADJUSTMENT`, `ROLLOUT_RESTART`, `SCALE_WORKLOAD`, `ROLLBACK_WORKLOAD`).
7. **Verification**: Verifies target workload reaches healthy ready state before resolving incident.
8. **Audit Trail**: Every action is immutably recorded in the audit log.

---

## 4. Verification & Testing

Run full test suite:

```bash
# Core Agent & Remediation Tests (57 passed)
python3 -m pytest --import-mode=prepend -v tests/

# Server Backend & Database API Tests (12 passed)
python3 -m pytest --import-mode=prepend -v cloud/tests/

# Frontend Type Check & Linter
npm run lint

# Production Build
npm run build
```

---

## 5. Security & Privacy

- **Zero SaaS Dependency**: No customer data or telemetry leaves your infrastructure.
- **RBAC Security**: Agent operates under least-privilege RBAC rules.
- **Secret Redaction**: Automatic redaction of environment variables, secrets, and auth tokens.
- **Human-in-the-Loop**: Destructive shell access is prohibited; state mutation requires human approval.
