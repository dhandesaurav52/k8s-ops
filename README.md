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

### Option A: Production Installation via Helm (Recommended)

SkyOps provides an official production-ready Helm chart located in `./deploy/chart`.

#### Minimal Production Installation

```bash
helm install skyops ./deploy/chart \
  --namespace skyops \
  --create-namespace \
  --set server.url="https://skyops.example.com"
```

#### Secure Installation with Secrets (Token & Gemini API Key)

```bash
helm install skyops ./deploy/chart \
  --namespace skyops \
  --create-namespace \
  --set server.url="https://skyops.example.com" \
  --set agent.token="YOUR_SECURE_AGENT_TOKEN" \
  --set gemini.apiKey="YOUR_GEMINI_API_KEY"
```

#### Installation with Custom Existing Kubernetes Secret

If you manage secrets externally (e.g. HashiCorp Vault, ExternalSecrets), provide your secret name containing `SKYOPS_AGENT_TOKEN` and `GEMINI_API_KEY`:

```bash
helm install skyops ./deploy/chart \
  --namespace skyops \
  --create-namespace \
  --set server.url="https://skyops.example.com" \
  --set existingSecret="my-skyops-credentials"
```

---

### Option B: Plain Kubernetes Manifests

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

## 3. Helm Configuration Parameters

The following table lists the main configurable parameters of the SkyOps chart and their default values:

| Parameter | Description | Default |
| :--- | :--- | :--- |
| `server.url` | SkyOps Server API base URL | `"http://skyops-server.skyops.svc.cluster.local:8000"` |
| `image.repository` | SkyOps Agent container image | `dhandesaurav52/skyops-agent` |
| `image.tag` | SkyOps Agent container tag | `"0.1.0"` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `agent.token` | Authentication secret token for Agent-to-Server requests | `""` |
| `gemini.apiKey` | Gemini API key for root cause diagnosis | `""` |
| `existingSecret` | Name of existing secret containing credentials | `""` |
| `agent.replicas` | Number of Agent pod replicas | `1` |
| `agent.resources.requests` | Requested CPU / Memory resources | `100m` / `128Mi` |
| `agent.resources.limits` | Limit CPU / Memory resources | `500m` / `512Mi` |
| `persistence.enabled` | Persistent storage for agent outbox queue | `false` (`emptyDir`) |
| `persistence.size` | Storage claim size if persistence is enabled | `1Gi` |
| `rbac.create` | Create ClusterRole and ClusterRoleBinding | `true` |
| `serviceAccount.create` | Create ServiceAccount for SkyOps | `true` |
| `securityContext.readOnlyRootFilesystem` | Enforce read-only root filesystem | `true` |
| `podSecurityContext.runAsNonRoot` | Run pod as non-root user (UID 10001) | `true` |

---

## 4. Chart Lifecycle Operations

### Upgrading a Release

To upgrade configuration or image version:

```bash
helm upgrade skyops ./deploy/chart \
  --namespace skyops \
  --set server.url="https://skyops.example.com"
```

### Rolling Back a Release

If an upgrade encounters issues, rollback cleanly to the previous revision:

```bash
helm rollback skyops 1 --namespace skyops
```

### Uninstalling SkyOps

To remove SkyOps agent resources from the cluster:

```bash
helm uninstall skyops --namespace skyops
kubectl delete namespace skyops
```

---

## 5. Troubleshooting & Diagnostics

- **Check Release Status**:
  ```bash
  helm status skyops -n skyops
  ```

- **Verify Agent Pod Health & Probes**:
  ```bash
  kubectl get pods -n skyops -o wide
  kubectl describe pod -l app.kubernetes.io/instance=skyops -n skyops
  ```

- **Stream Agent Telemetry Logs**:
  ```bash
  kubectl logs -n skyops -l app.kubernetes.io/instance=skyops -f
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

## 5. Agent ↔ Server Communication

- **Server URL Configuration**: The Agent connects to the SkyOps Server using `SKYOPS_SERVER_URL` (e.g. `http://skyops-server.skyops.svc.cluster.local:8000`). If not set, it falls back to `SKYOPS_CLOUD_URL` for backward compatibility or enters Local Stub mode if neither is configured.
- **Authentication**: All API requests from the Agent include `Authorization: Bearer <SKYOPS_AGENT_TOKEN>`. The token is read from environment secrets, redacted from logs and error messages, and verified on the server.
- **Incident Delivery & Contract**: Incidents captured by the Agent are serialized to JSON adhering strictly to the server's canonical schema. The field `state_history` supports both legacy string list representations and detailed state dictionaries.
- **Idempotent Upsert**: Incident submission (`POST /api/v1/incidents`) uses canonical incident IDs (`cluster_id` + resource identity) to prevent duplicate record creation during retries or Agent restarts.
- **Outbox & Retry Mechanics**: The Agent writes incidents to a thread-safe disk/memory Outbox queue. 
  - **Fatal Errors (401/403 Auth, 400/422 Validation)**: Fail fast to prevent infinite retry loops on non-recoverable client/credential errors.
  - **Transient Errors (5xx, 429, Connection Refused, Timeout)**: Retried with exponential backoff while retaining the item in the Outbox until successful delivery.
- **Health & Readiness Status**: The Agent exposes a health probe (`/health` and `/ready` on port 8080) reporting Kubernetes connectivity, SkyOps Server connection status, operational mode (`production` or `stub`), `cluster_id`, last successful synchronization timestamp, and pending Outbox item count.

---

## 6. Security & Privacy

- **Zero SaaS Dependency**: No customer data or telemetry leaves your infrastructure.
- **RBAC Security**: Agent operates under least-privilege RBAC rules.
- **Secret Redaction**: Automatic redaction of environment variables, secrets, and auth tokens.
- **Human-in-the-Loop**: Destructive shell access is prohibited; state mutation requires human approval.
