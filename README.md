# SkyOps — Self-Hosted Kubernetes Operations Platform

SkyOps is an enterprise-grade, self-hosted Kubernetes Observability, Root Cause Analysis & Safe Automated Remediation Platform. The customer owns the server, Web UI, API, database, and telemetry data in a self-contained Kubernetes deployment.

---

## 1. Target Architecture

```text
                  SELF-HOSTED KUBERNETES CLUSTER / INFRASTRUCTURE
       ┌─────────────────────────────────────────────────────────────────┐
       │                        SKYOPS PLATFORM                          │
       │                                                                 │
       │  ┌────────────────────────┐       ┌──────────────────────────┐  │
       │  │  SkyOps API + Web UI   │◄─────►│   PostgreSQL Database    │  │
       │  │  (FastAPI + React SPA) │       │   (Persistent Storage)   │  │
       │  └───────────▲────────────┘       └──────────────────────────┘  │
       │              │                                                  │
       │              │ HTTP REST + Auth Token                           │
       │              │                                                  │
       │  ┌───────────┴────────────┐                                     │
       │  │      SkyOps Agent      │                                     │
       │  │    (Cluster Watcher)   │                                     │
       │  └───────────┬────────────┘                                     │
       └──────────────┼──────────────────────────────────────────────────┘
                      │
                      ▼ Kubernetes API
            Workloads & Resources
```

---

## 2. Self-Hosted Installation (Single Helm Command)

SkyOps provides a complete, unified Helm chart (`./deploy/chart`) that provisions:
1. **PostgreSQL Database**: Persistent state storage for incidents, metrics, and audit logs.
2. **SkyOps API & Web UI Server**: Unified FastAPI backend and compiled React SPA static UI.
3. **SkyOps Agent**: Cluster event watcher, diagnostic engine, and safe remediation executor with full RBAC permissions.

### Prerequisites
- Kubernetes cluster (v1.24+)
- `helm` (v3+)
- `kubectl` configured with cluster admin permissions

---

### Step 1: Build & Push Docker Images

Build production container images locally or in your CI pipeline:

```bash
# 1. Build SkyOps API + Web UI Container Image
docker build -t skyops/api:0.1.0 -f cloud/Dockerfile .

# 2. Build SkyOps Agent Container Image
docker build -t skyops/agent:0.1.0 -f Dockerfile .
```

*Note: Both Dockerfiles utilize multi-stage builds and strict `.dockerignore` rules to ensure clean, lightweight images without `node_modules` pollution.*

---

### Step 2: Install via Helm (One Command)

Deploy the entire self-hosted platform with a single command:

```bash
helm install skyops ./deploy/chart \
  --namespace skyops \
  --create-namespace \
  --set agent.token="YOUR_SECURE_AGENT_TOKEN" \
  --set gemini.apiKey="YOUR_OPTIONAL_GEMINI_KEY"
```

---

### Step 3: Access the Web UI & API

Check the assigned service NodePort or port-forwarding details:

```bash
# Get NodePort URL
export NODE_PORT=$(kubectl get svc -n skyops skyops-api -o jsonpath='{.spec.ports[0].nodePort}')
export NODE_IP=$(kubectl get nodes -n skyops -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')

echo "SkyOps UI & API is accessible at: http://${NODE_IP}:${NODE_PORT}"
```

Or via kubectl port-forwarding:
```bash
kubectl port-forward -n skyops svc/skyops-api 8000:8000
# Open http://localhost:8000 in your browser
```

---

## 3. Helm Chart Configuration Parameters

| Parameter | Description | Default |
| :--- | :--- | :--- |
| `global.environment` | Deployment environment name | `"production"` |
| `agent.enabled` | Deploy SkyOps Agent pod | `true` |
| `agent.image.repository` | SkyOps Agent container image | `skyops/agent` |
| `agent.image.tag` | SkyOps Agent image tag | `"0.1.0"` |
| `agent.token` | Authentication secret token for Agent-to-Server requests | `"skyops-agent-secret-token"` |
| `api.image.repository` | SkyOps API + Web UI container image | `skyops/api` |
| `api.image.tag` | SkyOps API image tag | `"0.1.0"` |
| `api.service.type` | Kubernetes Service type for Web UI & API | `NodePort` |
| `api.service.port` | API Service port | `8000` |
| `api.service.nodePort` | Static NodePort for external browser access | `30800` |
| `api.adminUsername` | Admin UI login username | `"admin"` |
| `api.adminPassword` | Admin UI login password | `"skyops123"` |
| `postgresql.enabled` | Deploy self-hosted PostgreSQL database | `true` |
| `postgresql.auth.database` | Database name | `"skyops"` |
| `postgresql.auth.username` | Database username | `"skyops"` |
| `postgresql.auth.password` | Database password | `"skyops-pg-password"` |
| `postgresql.persistence.enabled` | Enable persistent volume claim for PostgreSQL | `true` |
| `postgresql.persistence.size` | Storage size for database PVC | `5Gi` |
| `rbac.create` | Create ClusterRole and ClusterRoleBinding | `true` |
| `serviceAccount.create` | Create ServiceAccount for Agent | `true` |
| `existingSecret` | Name of pre-created secret containing credentials | `""` |

---

## 4. Operational Lifecycle Commands

### Upgrading Configuration or Images

```bash
helm upgrade skyops ./deploy/chart \
  --namespace skyops \
  --set api.image.tag="0.1.1" \
  --set agent.image.tag="0.1.1"
```

### Rolling Back a Release

```bash
helm rollback skyops 1 --namespace skyops
```

### Uninstalling SkyOps

```bash
helm uninstall skyops --namespace skyops
kubectl delete namespace skyops
```

---

## 5. Troubleshooting & Health Verification

- **Check Pod Health**:
  ```bash
  kubectl get pods -n skyops
  ```

- **Check API & Migration Logs**:
  ```bash
  kubectl logs -n skyops -l app.kubernetes.io/component=api
  ```

- **Check Agent Telemetry**:
  ```bash
  kubectl logs -n skyops -l app.kubernetes.io/component=agent -f
  ```

- **Test Health Endpoint**:
  ```bash
  curl -s http://localhost:8000/health
  # Expected output: {"status":"healthy","database":"connected","timestamp":"..."}
  ```

---

## 6. Incident & Remediation Lifecycle Workflow

```text
DETECTED ──► INVESTIGATED ──► AI DIAGNOSIS ──► DRY RUN VALIDATION ──► HUMAN APPROVAL ──► SAFE EXECUTION ──► VERIFICATION ──► RESOLVED
```

1. **Detection**: Agent captures pod/workload failure events (`OOMKilled`, `CrashLoopBackOff`, `ImagePullBackOff`).
2. **Investigation**: Agent gathers pod status, events, controller spec, node state, and container logs without leaking secrets.
3. **AI Diagnosis**: Gemini AI or diagnostic engine analyzes evidence to determine exact root cause and actionable fix.
4. **Dry Run**: Validates policy compliance and target resource existence without mutating cluster state.
5. **Human Approval**: Operator reviews proposed command and grants approval.
6. **Execution**: Safe execution of allowlisted Kubernetes actions (`RESOURCE_ADJUSTMENT`, `ROLLOUT_RESTART`, `SCALE_WORKLOAD`, `ROLLBACK_WORKLOAD`).
7. **Verification**: Verifies target workload reaches healthy ready state before resolving incident.
8. **Audit Trail**: Every action is immutably recorded in the database audit log.

---

## 7. Verification & Automated Testing

Run the full test suite locally:

```bash
# Core Agent & Remediation Tests
python3 -m pytest --import-mode=prepend -v tests/

# Server Backend & Database API Tests
python3 -m pytest --import-mode=prepend -v cloud/tests/

# Frontend Type Check & Linter
npm run lint

# Production Build Test
npm run build
```

---

## 8. Security & Privacy

- **Zero SaaS Dependency**: 100% self-hosted on your own infrastructure.
- **RBAC Security**: Agent operates under explicit, least-privilege RBAC rules.
- **Secret Redaction**: Automatic redaction of environment variables, passwords, and auth tokens.
- **Human-in-the-Loop**: Destructive shell execution is strictly prohibited; state mutation requires human operator approval.
