# SkyOps — Self-Hosted Kubernetes Operations Platform (v1.0.0)

SkyOps is an enterprise-grade, self-hosted Kubernetes Observability, Root Cause Analysis & Safe Automated Remediation Platform. The customer owns the server, Web UI, API, database, and telemetry data in a self-contained Kubernetes deployment.

---

## 1. Executive Overview & Product Definition

SkyOps operates entirely inside your Kubernetes cluster. It continuously watches workload events (e.g., `CrashLoopBackOff`, `ImagePullBackOff`, `OOMKilled`, container crashes), correlates events into structured incident records, analyzes root causes with optional Gemini AI assistance, and presents operator-driven remediation controls via an intuitive Web UI.

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

### Customer Requirements (What is Needed)
- **Supported Kubernetes Cluster**: v1.24+ (EKS, GKE, AKS, OpenShift, RKE2, K3s, Kind, Minikube).
- **Tools**: `kubectl`, `helm` (v3+), cluster-admin permissions to create namespaces and RBAC resources.
- **Network Access**: Outbound access to pull container images from Docker Hub or your private registry.

### What is NOT Required on Customer Servers / Workstations
- **No Node.js / npm**
- **No Python / pip**
- **No Docker Desktop**
- **No Git**
- **No host-level compilation or development runtime**

### Minimum Resource Requirements
- **SkyOps API & Web UI**: 100m CPU request / 500m limit, 256Mi RAM request / 1Gi limit.
- **SkyOps Agent**: 100m CPU request / 500m limit, 128Mi RAM request / 512Mi limit.
- **PostgreSQL Database**: 100m CPU request / 500m limit, 256Mi RAM request / 512Mi limit, 5Gi PVC (ReadWriteOnce).

---

## 4. Self-Hosted Installation (Single Helm Command)

### Step 1: Add or Update Helm Chart Repository / Local Path

```bash
# Add SkyOps Helm repository (or use local ./deploy/chart directory)
helm install skyops ./deploy/chart \
  --namespace skyops-system \
  --create-namespace \
  --set api.image.repository="dhandesaurav52/skyops-api" \
  --set api.image.tag="1.0.0" \
  --set agent.image.repository="dhandesaurav52/skyops-agent" \
  --set agent.image.tag="1.0.0" \
  --set agent.token="SECURE_RANDOM_AGENT_TOKEN" \
  --set api.adminPassword="SECURE_ADMIN_PASSWORD" \
  --set postgresql.auth.password="SECURE_PG_PASSWORD"
```

### Step 2: Retrieve Initial Administrator Password & Complete Setup

When SkyOps is installed for the first time, an initial administrator password is automatically generated and saved in a Kubernetes Secret (similar to Jenkins).

1. **Retrieve the Initial Administrator Password using `kubectl`**:
```bash
kubectl get secret skyops-secrets -n skyops-system -o jsonpath="{.data.initial-admin-password}" | base64 --decode
```

2. **First-Run Initial Setup**:
   - Open the SkyOps Web UI in your browser (`http://${NODE_IP}:${NODE_PORT}`).
   - The **Initial Setup** wizard will prompt for the initial administrator password retrieved from the Kubernetes Secret.
   - Enter the initial password to unlock account creation.
   - Create your personal administrator credentials (username/email and password).
   - Once setup is completed, the **initial administrator password is automatically invalidated and disabled**.
   - Log in using your newly created administrator credentials to access the SkyOps Operations Console.

---

## 5. Security & Authentication Model

SkyOps V1 uses a simple, secure Jenkins-style local administrator authentication architecture:

- **Jenkins-style Bootstrap**: Fresh installations generate an initial password stored securely in `skyops-secrets` (`initial-admin-password`).
- **One-Time Setup Flow**: The initial password unlocks a 2-step setup wizard where the operator creates their administrator account with strong PBKDF2 password hashing. Once created, initial password authorization is permanently disabled.
- **Session Security**: Authenticated sessions issue HMAC-SHA256 tokens stored in HttpOnly, SameSite cookies.
- **Distinct Agent Auth**: SkyOps Agent authentication (`SKYOPS_AGENT_TOKEN`) remains completely separate from human operator credentials. Human administrator passwords are never shared with or used by cluster agents.
- **401 Enforcement**: All API routes (`/api/v1/clusters`, `/api/v1/incidents`, `/api/v1/remediations`, `/api/v1/metrics`) strictly enforce HTTP 401 Unauthorized responses for unauthenticated requests.

---

## 5. Configuration Parameters (Helm `values.yaml`)

| Parameter | Description | Default |
| :--- | :--- | :--- |
| `global.environment` | Deployment environment | `"production"` |
| `agent.enabled` | Deploy SkyOps Agent | `true` |
| `agent.image.repository` | SkyOps Agent container image | `dhandesaurav52/skyops-agent` |
| `agent.image.tag` | Agent image tag | `"1.0.0"` |
| `agent.token` | Authentication token for Agent-to-API communication | `"skyops-agent-secret-token"` |
| `api.image.repository` | SkyOps API + Web UI image | `dhandesaurav52/skyops-api` |
| `api.image.tag` | API image tag | `"1.0.0"` |
| `api.service.type` | Kubernetes Service type (`NodePort`, `LoadBalancer`, `ClusterIP`) | `NodePort` |
| `api.service.port` | Internal API port | `8000` |
| `api.service.nodePort` | External NodePort | `30800` |
| `api.adminUsername` | Admin username | `"admin"` |
| `api.adminPassword` | Admin password | `"skyops123"` |
| `postgresql.enabled` | Enable internal PostgreSQL deployment | `true` |
| `postgresql.auth.database` | Database name | `"skyops"` |
| `postgresql.auth.username` | Database username | `"skyops"` |
| `postgresql.auth.password` | Database password | `"skyops-pg-password"` |
| `postgresql.persistence.enabled` | Enable persistent storage for database | `true` |
| `postgresql.persistence.size` | Storage volume size | `5Gi` |
| `rbac.create` | Create ClusterRole and ClusterRoleBinding for Agent | `true` |
| `ingress.enabled` | Enable Ingress controller routing | `false` |

---

## 6. Operations Lifecycle

### Upgrading
```bash
helm upgrade skyops ./deploy/chart \
  --namespace skyops-system \
  --set api.image.tag="1.0.1" \
  --set agent.image.tag="1.0.1"
```

### Rolling Back
```bash
helm rollback skyops 1 --namespace skyops-system
```

### Uninstalling
```bash
helm uninstall skyops --namespace skyops-system
kubectl delete namespace skyops-system
```

---

## 7. Security & Compliance
- **Least Privilege RBAC**: Agent uses targeted read permissions for pods/events and scoped patch rights for deployments/statefulsets.
- **Zero SaaS Dependencies**: 100% self-hosted inside customer-controlled infrastructure.
- **Internal Database Security**: PostgreSQL service is `ClusterIP` only and never exposed externally.
- **Secret Redaction**: Automatic stripping of auth tokens, passwords, and sensitive keys in API logging and exception handlers.

---

## 8. Release Process for SkyOps v1.0.0
To build and release v1.0.0:
```bash
# 1. Build and Tag Images
docker build -t dhandesaurav52/skyops-api:1.0.0 -f cloud/Dockerfile .
docker build -t dhandesaurav52/skyops-agent:1.0.0 -f Dockerfile .

# 2. Push Images to Docker Hub
docker push dhandesaurav52/skyops-api:1.0.0
docker push dhandesaurav52/skyops-agent:1.0.0

# 3. Test Helm Lint & Render
helm lint deploy/chart
helm template skyops deploy/chart --namespace skyops-system
```
