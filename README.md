# SkyOps — Self-Hosted Kubernetes Incident & Investigation Platform (v1.0.0)

SkyOps is an enterprise-grade, self-hosted Kubernetes Observability, Incident Detection, Root Cause Analysis & Safe Automated Remediation Platform. The customer owns the server, Web UI, API, database, and telemetry data in a self-contained Kubernetes deployment.

---

## 1. Executive Overview & Product Definition

SkyOps operates entirely inside your Kubernetes cluster. It continuously watches workload events (e.g., `CrashLoopBackOff`, `ImagePullBackOff`, `OOMKilled`, container crashes), correlates events into structured incident records, analyzes root causes using deterministic Kubernetes rule sets, and presents operator-driven remediation controls via an intuitive Web UI.

---

## 2. Target Architecture

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
       │              │ (http://skyops-api:8000)                         │
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

## 3. Customer & System Requirements

### System Requirements
- **Supported Kubernetes Cluster**: v1.24+ (EKS, GKE, AKS, OpenShift, RKE2, K3s, Kind, Minikube).
- **Tools**: `kubectl`, `helm` (v3+), cluster-admin permissions to create namespaces and RBAC resources.
- **Network Access**: Internal HTTP/HTTPS communication between Agent and API (default: `http://skyops-api:8000`). Outbound image pull access from Docker Hub or private registry.

### What is NOT Required on Customer Servers / Workstations
- **No Node.js / npm**
- **No Python / pip**
- **No Docker Desktop**
- **No Git**
- **No host-level compilation or development runtime**

### Resource Requirements
- **SkyOps API & Web UI**: 100m CPU request / 500m limit, 256Mi RAM request / 1Gi limit.
- **SkyOps Agent**: 100m CPU request / 500m limit, 128Mi RAM request / 512Mi limit.
- **PostgreSQL Database**: 100m CPU request / 500m limit, 256Mi RAM request / 512Mi limit, 5Gi PVC (ReadWriteOnce).

---

## 4. Installation & Helm Setup

### Single Helm Command Installation

```bash
helm install skyops ./deploy/chart \
  --namespace skyops-system \
  --create-namespace \
  --set api.image.repository="dhandesaurav52/skyops-api" \
  --set api.image.tag="1.0.0" \
  --set agent.image.repository="dhandesaurav52/skyops-agent" \
  --set agent.image.tag="1.0.0"
```

---

## 5. First-Run Setup & Initial Password Retrieval

When SkyOps is installed on a fresh cluster, secure random credentials (initial administrator password, agent authentication token, secret key, and PostgreSQL password) are automatically generated and stored in a Kubernetes Secret named `skyops-secrets`.

### Step 1: Retrieve the Initial Administrator Password
Run the following `kubectl` command:
```bash
kubectl get secret skyops-secrets \
  -n skyops-system \
  -o jsonpath='{.data.SKYOPS_INITIAL_ADMIN_PASSWORD}' | base64 -d
```

### Step 2: Access the Web UI
Expose or access the API/UI service (`NodePort`, `LoadBalancer`, or `kubectl port-forward`):
```bash
kubectl port-forward svc/skyops-api 8000:8000 -n skyops-system
```
Open `http://localhost:8000` in your browser.

### Step 3: Complete First-Run Setup Wizard
1. The **First-Run Initial Setup** screen will prompt for the **Initial Administrator Password**.
2. Paste the password retrieved in Step 1 to unlock administrator creation.
3. Define your administrator credentials (username and password).
4. Upon successful setup, the initial administrator password is **permanently invalidated and disabled**.
5. Log in with your new administrator account to access the SkyOps dashboard.

---

## 6. How Authentication Works

SkyOps implements a secure first-run authentication flow:

- **Jenkins-Style First-Run**: Fresh installations initialize with a single-use initial password stored in `skyops-secrets`.
- **Admin Account Creation**: The setup wizard invalidates the initial password in the system configuration database as soon as the permanent administrator account is created.
- **Session Tokens**: Authenticated sessions issue signed session tokens passed via `Authorization: Bearer <token>` or HttpOnly cookies.
- **Agent Authentication**: The SkyOps Agent uses a dedicated, isolated token (`SKYOPS_AGENT_TOKEN`) for API synchronization. Agent tokens are completely separate from user credentials.
- **Strict 401 Unauthorized Enforcement**: Unauthenticated requests to protected endpoints (`/api/v1/clusters`, `/api/v1/incidents`, `/api/v1/remediations`, `/api/v1/metrics`) return `HTTP 401 Unauthorized`.

---

## 7. Connecting & Verifying the Agent

The SkyOps Agent automatically connects to the internal API (`http://skyops-api:8000`) using the shared `SKYOPS_AGENT_TOKEN` injected via environment variables.

### Verify Agent Connection
1. Check Agent Pod logs:
```bash
kubectl logs -l app.kubernetes.io/name=skyops-agent -n skyops-system
```
2. Verify Cluster Status in Web UI:
   - Navigate to **Clusters** in the SkyOps Web UI.
   - The cluster should display status **CONNECTED** with node count, pod count, and active heartbeat timestamps.

---

## 8. Configuration Parameters (Helm `values.yaml`)

| Parameter | Description | Default / Behavior |
| :--- | :--- | :--- |
| `global.environment` | Deployment environment | `"production"` |
| `agent.enabled` | Deploy SkyOps Agent | `true` |
| `agent.image.repository` | SkyOps Agent container image | `dhandesaurav52/skyops-agent` |
| `agent.image.tag` | Agent image tag | `"1.0.0"` |
| `agent.token` | Authentication token for Agent-to-API communication | Auto-generated on fresh install |
| `api.image.repository` | SkyOps API + Web UI image | `dhandesaurav52/skyops-api` |
| `api.image.tag` | API image tag | `"1.0.0"` |
| `api.service.type` | Kubernetes Service type (`NodePort`, `LoadBalancer`, `ClusterIP`) | `NodePort` |
| `api.service.port` | Internal API port | `8000` |
| `api.service.nodePort` | External NodePort | `30800` |
| `api.adminUsername` | Initial admin username | `"admin"` |
| `api.adminPassword` | Initial admin password override | Auto-generated on fresh install |
| `postgresql.enabled` | Enable internal PostgreSQL deployment | `true` |
| `postgresql.auth.database` | Database name | `"skyops"` |
| `postgresql.auth.username` | Database username | `"skyops"` |
| `postgresql.auth.password` | Database password override | Auto-generated on fresh install |
| `postgresql.persistence.enabled` | Enable persistent storage for database | `true` |
| `postgresql.persistence.size` | Storage volume size | `5Gi` |
| `rbac.create` | Create ClusterRole and ClusterRoleBinding for Agent | `true` |
| `ingress.enabled` | Enable Ingress controller routing | `false` |

---

## 9. Operations Lifecycle (Upgrade, Rollback, Uninstall)

### Upgrade
On `helm upgrade`, existing credential values in `skyops-secrets` are automatically preserved and never overwritten:
```bash
helm upgrade skyops ./deploy/chart \
  --namespace skyops-system \
  --set api.image.tag="1.0.1" \
  --set agent.image.tag="1.0.1"
```

### Rollback
```bash
helm rollback skyops 1 --namespace skyops-system
```

### Uninstall
```bash
helm uninstall skyops --namespace skyops-system
kubectl delete namespace skyops-system
```

---

## 10. Persistence & Backup Considerations

- **Database Persistence**: PersistentVolumeClaim (`skyops-postgres-pvc`, 5Gi ReadWriteOnce) stores PostgreSQL data files in `/var/lib/postgresql/data`.
- **Outbox Persistence**: The Agent maintains a local disk outbox queue (`data/outbox.json`) to store telemetry and incident events during temporary API/network disconnects.
- **Backup**: Backup the PostgreSQL database via `pg_dump` or Kubernetes volume snapshot before minor/major platform upgrades.

---

## 11. Troubleshooting Guide

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `401 Unauthorized` on Web UI login | Invalid setup credentials or expired session | Verify setup was completed; re-authenticate with created admin username and password. |
| Agent fails to register (`401` or `403`) | Mismatched `SKYOPS_AGENT_TOKEN` | Verify `SKYOPS_AGENT_TOKEN` matches between `skyops-secrets` and Agent env. |
| Database connection error (`503 Not Ready`) | PostgreSQL pod starting up or PVC unbound | Run `kubectl get pods -l app=postgresql -n skyops-system` and inspect logs. |
| Incident not showing in UI | Network disconnect or outbox queueing | Check agent logs for outbox sync attempts; outbox retries automatically with exponential backoff. |

---

## 12. Network & Firewall Requirements

- **Agent to API**: Port 8000 (HTTP/HTTPS internal service or NodePort).
- **API to PostgreSQL**: Port 5432 (Internal ClusterIP only, never exposed externally).
- **Operator to Web UI**: Port 8000 / 30800 (NodePort / Ingress / Port Forward).

---

## 13. RBAC Requirements

The SkyOps Agent requires targeted read access to workloads, pods, events, nodes, services, endpoints, persistent volumes, and scoped patch access to deployments/statefulsets for automated remediation.

Permissions configured in `deploy/chart/templates/rbac.yaml`:
- `pods`, `pods/log`, `events`, `nodes`, `services`, `endpoints`, `persistentvolumeclaims`, `persistentvolumes`, `configmaps` -> `get`, `list`, `watch`
- `deployments`, `statefulsets`, `replicasets`, `daemonsets` -> `get`, `list`, `watch`, `update`, `patch`

---

## 14. Verification Checklist

1. Deploy using `helm install skyops ./deploy/chart --namespace skyops-system --create-namespace`.
2. Extract initial password via `kubectl get secret skyops-secrets -n skyops-system -o jsonpath='{.data.SKYOPS_INITIAL_ADMIN_PASSWORD}' | base64 -d`.
3. Open `http://localhost:8000`, enter initial password, and create permanent administrator credentials.
4. Verify initial password can no longer unlock setup.
5. Log into SkyOps Web UI and confirm cluster state displays **CONNECTED**.
6. Trigger a test workload failure (e.g., image pull failure or crashing container) and verify incident creation, investigation findings, and remediation controls in the Web UI.
