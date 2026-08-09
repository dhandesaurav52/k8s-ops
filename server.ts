import express, { Request, Response } from 'express';
import path from 'path';
import fs from 'fs';
import { createServer as createViteServer } from 'vite';

const PORT = 3000;
const DB_FILE = path.join(process.cwd(), 'data', 'cloud_db.json');

// --- Seed Data ---
const SEED_CLUSTERS = [
  {
    cluster_id: 'skyops-cluster-prod-us',
    name: 'prod-us-east-1a',
    status: 'CONNECTED',
    kubernetes_version: 'v1.28.4-gke',
    node_count: 8,
    pod_count: 142,
    namespace_count: 12,
    agent_status: 'HEALTHY',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    last_seen: new Date().toISOString(),
  },
  {
    cluster_id: 'skyops-cluster-staging-eu',
    name: 'staging-eu-west-1',
    status: 'CONNECTED',
    kubernetes_version: 'v1.29.1-k3s',
    node_count: 4,
    pod_count: 58,
    namespace_count: 6,
    agent_status: 'HEALTHY',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    last_seen: new Date().toISOString(),
  },
  {
    cluster_id: 'skyops-cluster-dev-local',
    name: 'local-minikube',
    status: 'STUB',
    kubernetes_version: 'v1.27.2',
    node_count: 1,
    pod_count: 18,
    namespace_count: 3,
    agent_status: 'LOCAL_DEV',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    last_seen: new Date().toISOString(),
  },
];

const SEED_INCIDENTS = [
  {
    id: 1,
    cluster_id: 'skyops-cluster-prod-us',
    incident_id: 'INC-0842',
    category: 'OOMKilled',
    status: 'OPEN',
    current_state: 'app-service: OOMKilled (Exit Code 137, Restarts: 14)',
    severity: 'CRITICAL',
    occurrences: 14,
    first_seen: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    last_seen: new Date(Date.now() - 1000 * 30).toISOString(),
    created_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    updated_at: new Date(Date.now() - 1000 * 30).toISOString(),
    resolved_at: null,
    resource_kind: 'Pod',
    resource_namespace: 'payments',
    resource_name: 'payment-processor-79d8b8584f-x2k9l',
    resource_uid: 'uid-pay-proc-882194',
    diagnosis: {
      category: 'OOMKilled',
      severity: 'CRITICAL',
      confidence: 0.96,
      reason: 'Container process memory limit exceeded',
      root_cause: 'The payment-processor container exceeded its configured memory limit of 512Mi (peak RSS observed: 524Mi) during payload batching. The Linux kernel OOM-killer terminated process PID 1 with exit code 137.',
      actionable_recommendation: 'Increase container memory limit in Deployment spec from 512Mi to 1Gi.',
      mitigation_command: 'kubectl patch deployment payment-processor -n payments --type=json -p=\'[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "1Gi"}]\''
    },
    investigation: {
      pod_phase: 'Running',
      node_name: 'gke-prod-pool-1-8a9d02',
      pod_ip: '10.244.2.89',
      container_states: [
        {
          name: 'payment-processor',
          image: 'registry.internal.net/payments/processor:v2.14.1',
          ready: false,
          restart_count: 14,
          state_type: 'terminated',
          reason: 'OOMKilled',
          exit_code: 137,
        },
      ],
      kubernetes_events: [
        { type: 'Warning', reason: 'Unhealthy', message: 'Liveness probe failed', count: 8, last_timestamp: new Date().toISOString() },
        { type: 'Warning', reason: 'OOMKilling', message: 'Memory cgroup out of memory: Killed process 31920', count: 14, last_timestamp: new Date().toISOString() },
      ],
      recent_logs: [
        '[INFO] Processing batch settlement payload ID: #SETT-88912',
        '[WARN] Heap allocation high: 489.2MB / 512.0MB (95.5% utilization)',
        '[FATAL] KERNEL: OOM-killer invoker: task=node, pid=31920',
      ],
      metrics_summary: { cpu_usage_mcores: 210, memory_usage_mb: 512, memory_limit_mb: 512 },
    },
    ai_analysis: {
      status: 'COMPLETED',
      summary: 'Critical OOMKilled cascade on payment-processor pod due to unexpected spike in settlement payload size exceeding 512Mi limit.',
      detailed_explanation: 'Analysis confirms CGroups SIGKILL triggered by memory exhaustion on gke-prod-pool-1-8a9d02.',
      probable_causes: ['Memory limit set too low (512Mi)', 'In-memory buffer leak in reconciliation library'],
      remediation_steps: ['Patch Deployment limits to 1.5Gi memory limit.', 'Apply vertical pod autoscaler.'],
      suggested_kubectl: ['kubectl describe pod payment-processor-79d8b8584f-x2k9l -n payments'],
      analyzed_at: new Date().toISOString(),
    },
    state_history: ['Pending', 'Running', 'OOMKilled'],
  },
  {
    id: 2,
    cluster_id: 'skyops-cluster-prod-us',
    incident_id: 'INC-0841',
    category: 'ImagePullFailure',
    status: 'OPEN',
    current_state: 'auth-gateway: ErrImagePull (Failed to pull image "registry.internal.net/auth/gateway:v3.0.0-rc1")',
    severity: 'HIGH',
    occurrences: 6,
    first_seen: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    last_seen: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    created_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    updated_at: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    resolved_at: null,
    resource_kind: 'Pod',
    resource_namespace: 'authentication',
    resource_name: 'auth-gateway-6d7c4f4b9d-4m87q',
    resource_uid: 'uid-auth-gate-99120',
    diagnosis: {
      category: 'ImagePullFailure',
      severity: 'HIGH',
      confidence: 0.98,
      reason: 'Container image tag or pull secret invalid',
      root_cause: 'Registry returned HTTP 404 for image tag v3.0.0-rc1.',
      actionable_recommendation: 'Revert deployment image tag to v2.9.4.',
      mitigation_command: 'kubectl set image deployment/auth-gateway auth-gateway=registry.internal.net/auth/gateway:v2.9.4 -n authentication'
    },
    investigation: {
      pod_phase: 'Pending',
      node_name: 'gke-prod-pool-1-8a9d03',
      pod_ip: '10.244.3.112',
      container_states: [
        {
          name: 'auth-gateway',
          image: 'registry.internal.net/auth/gateway:v3.0.0-rc1',
          ready: false,
          restart_count: 0,
          state_type: 'waiting',
          reason: 'ImagePullBackOff',
        },
      ],
      kubernetes_events: [
        { type: 'Warning', reason: 'Failed', message: 'Failed to pull image: manifest unknown', count: 4, last_timestamp: new Date().toISOString() },
      ],
      recent_logs: [],
      metrics_summary: { cpu_usage_mcores: 0, memory_usage_mb: 0, memory_limit_mb: 256 },
    },
    ai_analysis: {
      status: 'COMPLETED',
      summary: 'Image pull error blocking deployment rollouts on auth-gateway service.',
      detailed_explanation: 'Tag v3.0.0-rc1 is missing in the internal container registry.',
      probable_causes: ['CI pipeline tag push failed', 'Typo in image tag'],
      remediation_steps: ['Rollback deployment image spec to v2.9.4'],
      suggested_kubectl: ['kubectl rollout undo deployment/auth-gateway -n authentication'],
      analyzed_at: new Date().toISOString(),
    },
    state_history: ['Pending', 'ErrImagePull', 'ImagePullBackOff'],
  },
  {
    id: 3,
    cluster_id: 'skyops-cluster-staging-eu',
    incident_id: 'INC-0839',
    category: 'CrashLoopBackOff',
    status: 'OPEN',
    current_state: 'redis-cache: CrashLoopBackOff (Back-off restarting failed container)',
    severity: 'MEDIUM',
    occurrences: 9,
    first_seen: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
    last_seen: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
    created_at: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
    updated_at: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
    resolved_at: null,
    resource_kind: 'Pod',
    resource_namespace: 'cache',
    resource_name: 'redis-master-0',
    resource_uid: 'uid-redis-sts-001',
    diagnosis: {
      category: 'CrashLoopBackOff',
      severity: 'MEDIUM',
      confidence: 0.94,
      reason: 'Configuration file parse error',
      root_cause: 'Invalid directive maxmemory-policy-v2 on line 42 of redis.conf.',
      actionable_recommendation: 'Fix ConfigMap syntax error, then restart pod.',
      mitigation_command: 'kubectl rollout restart statefulset/redis-master -n cache'
    },
    investigation: {
      pod_phase: 'Running',
      node_name: 'staging-worker-02',
      pod_ip: '10.244.1.42',
      container_states: [
        {
          name: 'redis',
          image: 'redis:7.2-alpine',
          ready: false,
          restart_count: 9,
          state_type: 'waiting',
          reason: 'CrashLoopBackOff',
        },
      ],
      kubernetes_events: [
        { type: 'Warning', reason: 'BackOff', message: 'Back-off restarting failed container', count: 24, last_timestamp: new Date().toISOString() },
      ],
      recent_logs: ['Fatal error: Bad directive "maxmemory-policy-v2" on line 42'],
      metrics_summary: { cpu_usage_mcores: 5, memory_usage_mb: 12, memory_limit_mb: 256 },
    },
    ai_analysis: {
      status: 'COMPLETED',
      summary: 'Redis cache master crashing continuously due to invalid configuration directive.',
      detailed_explanation: 'Syntax error in redis.conf mounted from ConfigMap redis-config.',
      probable_causes: ['ConfigMap edit error during staging maintenance'],
      remediation_steps: ['Update ConfigMap and delete pod to trigger re-creation'],
      suggested_kubectl: ['kubectl edit configmap redis-config -n cache'],
      analyzed_at: new Date().toISOString(),
    },
    state_history: ['Running', 'Terminated', 'CrashLoopBackOff'],
  },
];

// --- Persistent Database Interface ---
interface CloudStore {
  clusters: any[];
  incidents: any[];
  nextIncidentDbId: number;
}

function loadStore(): CloudStore {
  try {
    const dataDir = path.dirname(DB_FILE);
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }

    if (fs.existsSync(DB_FILE)) {
      const raw = fs.readFileSync(DB_FILE, 'utf-8');
      const parsed = JSON.parse(raw);
      if (parsed && Array.isArray(parsed.clusters) && Array.isArray(parsed.incidents)) {
        return parsed;
      }
    }
  } catch (e) {
    console.warn('[SkyOps Cloud] Could not read db file, creating new seed store:', e);
  }

  const initialStore: CloudStore = {
    clusters: SEED_CLUSTERS,
    incidents: SEED_INCIDENTS,
    nextIncidentDbId: 10,
  };
  saveStore(initialStore);
  return initialStore;
}

function saveStore(store: CloudStore) {
  try {
    const dataDir = path.dirname(DB_FILE);
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }
    fs.writeFileSync(DB_FILE, JSON.stringify(store, null, 2), 'utf-8');
  } catch (e) {
    console.error('[SkyOps Cloud] Failed to save DB file:', e);
  }
}

let store = loadStore();

async function startServer() {
  const app = express();
  app.use(express.json());

  // CORS middleware
  app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, PATCH, PUT, DELETE, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');
    if (req.method === 'OPTIONS') {
      return res.sendStatus(200);
    }
    next();
  });

  // --- Health Endpoints ---
  app.get(['/health', '/api/v1/health'], (req: Request, res: Response) => {
    res.json({
      status: 'ok',
      service: 'SkyOps Cloud Backend',
      version: '1.0.0',
      timestamp: new Date().toISOString(),
    });
  });

  // --- Clusters Endpoints ---
  app.get('/api/v1/clusters', (req: Request, res: Response) => {
    res.json(store.clusters);
  });

  app.post('/api/v1/clusters', (req: Request, res: Response) => {
    const body = req.body || {};
    const clusterId = body.cluster_id;
    if (!clusterId) {
      return res.status(400).json({ detail: 'cluster_id is required' });
    }

    const now = new Date().toISOString();
    let existing = store.clusters.find((c) => c.cluster_id === clusterId);
    if (existing) {
      existing.name = body.name || existing.name;
      existing.kubernetes_version = body.kubernetes_version || existing.kubernetes_version;
      existing.status = body.status || existing.status;
      existing.node_count = body.node_count ?? existing.node_count;
      existing.pod_count = body.pod_count ?? existing.pod_count;
      existing.namespace_count = body.namespace_count ?? existing.namespace_count;
      existing.agent_status = body.agent_status || 'HEALTHY';
      existing.updated_at = now;
      existing.last_seen = now;
      saveStore(store);
      return res.status(200).json(existing);
    }

    const newCluster = {
      cluster_id: clusterId,
      name: body.name || clusterId,
      status: body.status || 'CONNECTED',
      kubernetes_version: body.kubernetes_version || 'v1.28.0',
      node_count: body.node_count || 1,
      pod_count: body.pod_count || 0,
      namespace_count: body.namespace_count || 1,
      agent_status: 'HEALTHY',
      created_at: now,
      updated_at: now,
      last_seen: now,
    };
    store.clusters.push(newCluster);
    saveStore(store);
    return res.status(201).json(newCluster);
  });

  app.get('/api/v1/clusters/:cluster_id', (req: Request, res: Response) => {
    const cluster = store.clusters.find((c) => c.cluster_id === req.params.cluster_id);
    if (!cluster) {
      return res.status(404).json({ detail: `Cluster '${req.params.cluster_id}' not found` });
    }
    res.json(cluster);
  });

  app.patch('/api/v1/clusters/:cluster_id', (req: Request, res: Response) => {
    const cluster = store.clusters.find((c) => c.cluster_id === req.params.cluster_id);
    if (!cluster) {
      return res.status(404).json({ detail: `Cluster '${req.params.cluster_id}' not found` });
    }
    Object.assign(cluster, req.body, { updated_at: new Date().toISOString() });
    saveStore(store);
    res.json(cluster);
  });

  // --- Incidents Endpoints ---
  app.get('/api/v1/incidents', (req: Request, res: Response) => {
    const { cluster_id, status: statusParam, skip, limit } = req.query;
    let list = [...store.incidents];

    if (cluster_id && typeof cluster_id === 'string' && cluster_id !== 'ALL') {
      list = list.filter((i) => i.cluster_id === cluster_id);
    }
    if (statusParam && typeof statusParam === 'string' && statusParam !== 'ALL') {
      list = list.filter((i) => i.status?.toUpperCase() === statusParam.toUpperCase());
    }

    // Sort newest first
    list.sort((a, b) => new Date(b.created_at || b.first_seen).getTime() - new Date(a.created_at || a.first_seen).getTime());

    const skipNum = parseInt(skip as string, 10) || 0;
    const limitNum = parseInt(limit as string, 10) || 1000;
    const paginated = list.slice(skipNum, skipNum + limitNum);

    res.json(paginated);
  });

  app.post('/api/v1/incidents', (req: Request, res: Response) => {
    const body = req.body || {};
    const clusterId = body.cluster_id;
    const incidentId = body.incident_id;

    if (!clusterId || !incidentId) {
      return res.status(400).json({ detail: 'cluster_id and incident_id are required' });
    }

    const now = new Date().toISOString();

    // Auto-register cluster if not present
    let cluster = store.clusters.find((c) => c.cluster_id === clusterId);
    if (!cluster) {
      cluster = {
        cluster_id: clusterId,
        name: clusterId,
        status: 'CONNECTED',
        kubernetes_version: 'v1.28.0',
        node_count: 1,
        pod_count: 1,
        namespace_count: 1,
        agent_status: 'HEALTHY',
        created_at: now,
        updated_at: now,
        last_seen: now,
      };
      store.clusters.push(cluster);
    } else {
      cluster.last_seen = now;
      cluster.updated_at = now;
    }

    // Find existing by (cluster_id, incident_id) or active open incident on same resource_uid
    const resourceUid = body.resource_uid || body.resource?.uid || '';
    let existing = store.incidents.find(
      (i) =>
        (i.cluster_id === clusterId && i.incident_id === incidentId) ||
        (resourceUid && i.cluster_id === clusterId && i.resource_uid === resourceUid && i.status === 'OPEN')
    );

    if (existing) {
      existing.category = body.category || existing.category;
      existing.current_state = body.current_state || existing.current_state;
      existing.severity = body.severity || existing.severity;
      existing.occurrences = body.occurrences || existing.occurrences + 1;
      existing.updated_at = now;
      existing.last_seen = now;
      if (body.status) {
        existing.status = body.status;
        if (body.status === 'RESOLVED' && !existing.resolved_at) {
          existing.resolved_at = now;
        }
      }
      if (body.diagnosis) existing.diagnosis = body.diagnosis;
      if (body.investigation) existing.investigation = body.investigation;
      if (body.ai_analysis) existing.ai_analysis = body.ai_analysis;
      if (body.state_history) existing.state_history = body.state_history;

      saveStore(store);
      return res.status(200).json(existing);
    }

    // Create new incident
    const newDbId = store.nextIncidentDbId++;
    const newIncident = {
      id: newDbId,
      cluster_id: clusterId,
      incident_id: incidentId,
      category: body.category || 'Unknown',
      status: body.status || 'OPEN',
      current_state: body.current_state || '',
      severity: body.severity || 'MEDIUM',
      occurrences: body.occurrences || 1,
      resource_kind: body.resource_kind || body.resource?.kind || 'Pod',
      resource_namespace: body.resource_namespace || body.resource?.namespace || 'default',
      resource_name: body.resource_name || body.resource?.name || 'unknown',
      resource_uid: resourceUid,
      diagnosis: body.diagnosis || {},
      investigation: body.investigation || {},
      ai_analysis: body.ai_analysis || {},
      state_history: body.state_history || [body.category || 'Detected'],
      first_seen: now,
      last_seen: now,
      created_at: now,
      updated_at: now,
      resolved_at: body.status === 'RESOLVED' ? now : null,
    };

    store.incidents.unshift(newIncident);
    saveStore(store);
    return res.status(201).json(newIncident);
  });

  app.get('/api/v1/incidents/:key', (req: Request, res: Response) => {
    const key = req.params.key;
    const clusterId = req.query.cluster_id as string;

    let found = store.incidents.find((i) => i.id.toString() === key || i.incident_id === key);
    if (!found && clusterId) {
      found = store.incidents.find((i) => i.cluster_id === clusterId && i.incident_id === key);
    }

    if (!found) {
      return res.status(404).json({ detail: `Incident '${key}' not found` });
    }
    res.json(found);
  });

  app.patch('/api/v1/incidents/:id', (req: Request, res: Response) => {
    const id = parseInt(req.params.id, 10);
    const existing = store.incidents.find((i) => i.id === id);
    if (!existing) {
      return res.status(404).json({ detail: `Incident with ID ${id} not found` });
    }

    const now = new Date().toISOString();
    Object.assign(existing, req.body, { updated_at: now });
    if (req.body.status === 'RESOLVED' && !existing.resolved_at) {
      existing.resolved_at = now;
    } else if (req.body.status === 'OPEN') {
      existing.resolved_at = null;
    }

    saveStore(store);
    res.json(existing);
  });

  app.post('/api/v1/incidents/:id/resolve', (req: Request, res: Response) => {
    const key = req.params.id;
    const existing = store.incidents.find(
      (i) => i.id.toString() === key || i.incident_id === key
    );

    if (!existing) {
      return res.status(404).json({ detail: `Incident '${key}' not found` });
    }

    const now = new Date().toISOString();
    existing.status = 'RESOLVED';
    existing.resolved_at = now;
    existing.updated_at = now;
    if (!existing.state_history) existing.state_history = [];
    existing.state_history.push('Resolved');

    saveStore(store);
    res.json(existing);
  });

  // --- Vite & Production Static File Handler ---
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req: Request, res: Response) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[SkyOps Cloud] Backend & UI running on http://0.0.0.0:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error('[SkyOps Cloud] Failed to start server:', err);
  process.exit(1);
});
