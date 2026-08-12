import { Router, Request, Response } from 'express';

export const fallbackRouter = Router();

// Health check
fallbackRouter.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'healthy', service: 'SkyOps Express Fallback Server', version: '1.0.0' });
});

// Clusters
fallbackRouter.get('/clusters', (req: Request, res: Response) => {
  res.json([
    {
      id: 1,
      cluster_id: 'skyops-cluster-prod-us',
      name: 'prod-us-east-1a',
      kubernetes_version: 'v1.28.4-gke',
      status: 'CONNECTED',
      node_count: 8,
      pod_count: 142,
      namespace_count: 12,
      last_seen: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: 2,
      cluster_id: 'skyops-cluster-staging-eu',
      name: 'staging-eu-west-1b',
      kubernetes_version: 'v1.28.2-gke',
      status: 'CONNECTED',
      node_count: 4,
      pod_count: 68,
      namespace_count: 8,
      last_seen: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ]);
});

fallbackRouter.get('/clusters/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  res.json({
    id: 1,
    cluster_id: id,
    name: id.includes('prod') ? 'prod-us-east-1a' : 'staging-eu-west-1b',
    kubernetes_version: 'v1.28.4-gke',
    status: 'CONNECTED',
    node_count: 8,
    pod_count: 142,
    namespace_count: 12,
    last_seen: new Date().toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  });
});

// Default Mock Metrics Data
const getDefaultMetrics = (cid: string) => {
  const nowIso = new Date().toISOString();
  return {
    cluster_id: cid,
    metrics_status: 'ONLINE',
    status_message: 'Live metrics reported by SkyOps agent (metrics.k8s.io)',
    source: 'metrics.k8s.io',
    last_collected: nowIso,
    summary: {
      total_cpu_mcores: 32000,
      used_cpu_mcores: 18400,
      cpu_utilization_pct: 57.5,
      total_memory_mb: 131072,
      used_memory_mb: 84200,
      memory_utilization_pct: 64.2,
    },
    nodes: [
      {
        name: 'gke-prod-pool-1-8a9d01',
        cluster_id: cid,
        status: 'Ready',
        cpu_usage_mcores: 2400,
        cpu_capacity_mcores: 4000,
        cpu_pct: 60,
        memory_usage_mb: 10500,
        memory_capacity_mb: 16384,
        memory_pct: 64,
      },
      {
        name: 'gke-prod-pool-1-8a9d02',
        cluster_id: cid,
        status: 'Ready',
        cpu_usage_mcores: 2200,
        cpu_capacity_mcores: 4000,
        cpu_pct: 55,
        memory_usage_mb: 9800,
        memory_capacity_mb: 16384,
        memory_pct: 60,
      },
      {
        name: 'gke-prod-pool-1-8a9d03',
        cluster_id: cid,
        status: 'Ready',
        cpu_usage_mcores: 2800,
        cpu_capacity_mcores: 4000,
        cpu_pct: 70,
        memory_usage_mb: 11200,
        memory_capacity_mb: 16384,
        memory_pct: 68,
      },
    ],
    pods: [
      {
        name: 'payment-api-worker-7f8d9b',
        namespace: 'payments',
        cluster_id: cid,
        node_name: 'gke-prod-pool-1-8a9d02',
        cpu_usage_mcores: 480,
        memory_usage_mb: 820,
        restarts: 4,
      },
      {
        name: 'catalog-service-5d6c7e',
        namespace: 'catalog',
        cluster_id: cid,
        node_name: 'gke-prod-pool-1-8a9d01',
        cpu_usage_mcores: 310,
        memory_usage_mb: 450,
        restarts: 0,
      },
      {
        name: 'postgres-db-0',
        namespace: 'database',
        cluster_id: cid,
        node_name: 'gke-prod-pool-1-8a9d03',
        cpu_usage_mcores: 890,
        memory_usage_mb: 3400,
        restarts: 0,
      },
    ],
  };
};

// Metrics
fallbackRouter.get('/metrics', (req: Request, res: Response) => {
  const cid = (req.query.cluster_id as string) || 'skyops-cluster-prod-us';
  res.json(getDefaultMetrics(cid));
});

fallbackRouter.get('/metrics/nodes', (req: Request, res: Response) => {
  const cid = (req.query.cluster_id as string) || 'skyops-cluster-prod-us';
  res.json(getDefaultMetrics(cid).nodes);
});

fallbackRouter.get('/metrics/pods', (req: Request, res: Response) => {
  const cid = (req.query.cluster_id as string) || 'skyops-cluster-prod-us';
  res.json(getDefaultMetrics(cid).pods);
});

fallbackRouter.get('/metrics/history', (req: Request, res: Response) => {
  const cid = (req.query.cluster_id as string) || 'skyops-cluster-prod-us';
  const range = (req.query.range as string) || '1h';

  const now = Math.floor(Date.now() / 1000);
  const points = [];
  for (let i = 11; i >= 0; i--) {
    const ptDate = new Date((now - i * 300) * 1000);
    const hours = ptDate.getUTCHours().toString().padStart(2, '0');
    const mins = ptDate.getUTCMinutes().toString().padStart(2, '0');
    points.push({
      timestamp: ptDate.toISOString(),
      timeLabel: `${hours}:${mins}`,
      cpu_pct: 57.5 + (Math.random() * 4 - 2),
      memory_pct: 64.2 + (Math.random() * 2 - 1),
      cpu_mcores: 18400,
      memory_mb: 84148,
    });
  }

  res.json({
    cluster_id: cid,
    time_range: range,
    metrics_status: 'ONLINE',
    points,
  });
});

// Incidents in-memory store
const inMemoryIncidents: any[] = [
  {
    id: 1,
    cluster_id: 'skyops-cluster-prod-us',
    incident_id: 'INC-1042',
    category: 'OOMKilled',
    status: 'OPEN',
    severity: 'CRITICAL',
    current_state: 'payment-api: OOMKilled (Exit code 137, Restarts: 4)',
    occurrences: 4,
    created_at: new Date(Date.now() - 3600000).toISOString(),
    updated_at: new Date().toISOString(),
    resource_kind: 'Pod',
    resource_namespace: 'payments',
    resource_name: 'payment-api-worker-7f8d9b',
    resource_uid: 'uid-payment-7f8d9b',
    diagnosis: {
      category: 'OOMKilled',
      severity: 'CRITICAL',
      confidence: 0.95,
      reason: 'Process cgroup RSS memory limit exceeded',
      root_cause: 'Container payment-api hit memory limit 256Mi during payload processing. SIGKILL triggered by cgroup manager.',
      actionable_recommendation: 'Increase pod memory request to 512Mi and limit to 1Gi in Deployment spec.',
      mitigation_command: `kubectl patch deployment payment-api-worker -n payments -p '{"spec":{"template":{"spec":{"containers":[{"name":"app","resources":{"limits":{"memory":"1Gi"}}}]}}}}'`,
    },
    investigation: {
      pod_phase: 'Running',
      node_name: 'gke-prod-pool-1-8a9d02',
      pod_ip: '10.244.2.191',
      container_states: [
        {
          name: 'payment-api',
          image: 'registry.internal.net/payments/api:v1.9.0',
          ready: false,
          restart_count: 4,
          state_type: 'terminated',
          reason: 'OOMKilled',
          exit_code: 137,
        },
      ],
      kubernetes_events: [
        { type: 'Warning', reason: 'OOMKilling', message: 'Memory cgroup out of memory: Killed process pid=19420 (node)', count: 4, last_timestamp: new Date().toISOString() },
      ],
      recent_logs: [
        '[WARN] Heap usage reaching 98% threshold',
        '[FATAL] Out of memory: Kill process 19420 (node)',
      ],
      metrics_summary: { cpu_usage_mcores: 180, memory_usage_mb: 256, memory_limit_mb: 256 },
    },
    ai_analysis: {
      status: 'COMPLETED',
      summary: 'Newly detected OOMKilled crash on payment-api-worker pod.',
      detailed_explanation: 'Agent telemetry captured kernel SIGKILL exit code 137 on payment-api container.',
      probable_causes: ['Insufficient container memory limit', 'Memory leak in transaction handler'],
      remediation_steps: ['Increase container memory limits', 'Analyze heap dumps using pprof'],
      suggested_kubectl: ['kubectl describe pod payment-api-worker-7f8d9b -n payments'],
      analyzed_at: new Date().toISOString(),
    },
    state_history: ['Pending', 'Running', 'OOMKilled'],
  },
];

fallbackRouter.get('/incidents', (req: Request, res: Response) => {
  const { cluster_id, status } = req.query;
  let filtered = [...inMemoryIncidents];
  if (cluster_id && cluster_id !== 'ALL') {
    filtered = filtered.filter((i) => i.cluster_id === cluster_id);
  }
  if (status && status !== 'ALL') {
    filtered = filtered.filter((i) => i.status === status);
  }
  res.json(filtered);
});

fallbackRouter.post('/incidents', (req: Request, res: Response) => {
  const newIncident = {
    id: inMemoryIncidents.length + 1,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...req.body,
  };
  inMemoryIncidents.unshift(newIncident);
  res.status(201).json(newIncident);
});

fallbackRouter.get('/incidents/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  const inc = inMemoryIncidents.find((i) => String(i.id) === id || i.incident_id === id);
  if (!inc) {
    return res.status(404).json({ detail: 'Incident not found' });
  }
  res.json(inc);
});

fallbackRouter.post('/incidents/:id/resolve', (req: Request, res: Response) => {
  const { id } = req.params;
  const inc = inMemoryIncidents.find((i) => String(i.id) === id || i.incident_id === id);
  if (inc) {
    inc.status = 'RESOLVED';
    inc.resolved_at = new Date().toISOString();
  }
  res.json({ status: 'RESOLVED', id });
});

// Remediations
fallbackRouter.get('/remediations', (req: Request, res: Response) => {
  res.json([]);
});

fallbackRouter.get('/remediations/audit', (req: Request, res: Response) => {
  res.json([]);
});

fallbackRouter.get('/remediations/:id', (req: Request, res: Response) => {
  res.status(404).json({ detail: 'Remediation plan not found' });
});

let fallbackSetupCompleted = false;
let fallbackUsers: Record<string, string> = {};

fallbackRouter.get(['/auth/status', '/v1/auth/status'], (req: Request, res: Response) => {
  res.json({
    is_setup_completed: fallbackSetupCompleted,
    authenticated: false,
    user: null,
  });
});

fallbackRouter.post(['/auth/verify-initial-password', '/v1/auth/verify-initial-password'], (req: Request, res: Response) => {
  if (fallbackSetupCompleted) {
    return res.status(400).json({ detail: "Initial setup has already been completed." });
  }
  const initPass = req.body?.initial_password;
  if (initPass === "skyops123" || initPass === "skyops-initial-admin-password") {
    return res.json({ status: "ok", message: "Initial password verified" });
  }
  return res.status(401).json({ detail: "Invalid initial administrator password." });
});

fallbackRouter.post(['/auth/setup-admin', '/v1/auth/setup-admin'], (req: Request, res: Response) => {
  if (fallbackSetupCompleted) {
    return res.status(400).json({ detail: "Initial setup has already been completed." });
  }
  const { initial_password, username, password } = req.body || {};
  if (initial_password !== "skyops123" && initial_password !== "skyops-initial-admin-password") {
    return res.status(401).json({ detail: "Invalid initial administrator password." });
  }
  if (!username || !password) {
    return res.status(400).json({ detail: "Username and password required." });
  }
  fallbackUsers[username.toLowerCase()] = password;
  fallbackSetupCompleted = true;
  res.status(201).json({ status: "ok", message: "Administrator account created successfully." });
});

fallbackRouter.post(['/auth/login', '/v1/auth/login'], (req: Request, res: Response) => {
  const { username, password } = req.body || {};
  if (!fallbackSetupCompleted) {
    return res.status(400).json({ detail: "Initial setup not completed." });
  }
  const storedPass = fallbackUsers[username?.toLowerCase()];
  if (storedPass && storedPass === password) {
    return res.json({
      status: "ok",
      user: { username, role: "admin" },
      token: "skyops-session-token",
    });
  }
  return res.status(401).json({ detail: "Invalid username or password." });
});

fallbackRouter.post(['/auth/logout', '/v1/auth/logout'], (req: Request, res: Response) => {
  res.json({ status: "logged_out" });
});

fallbackRouter.get(['/auth/me', '/v1/auth/me'], (req: Request, res: Response) => {
  res.json({ authenticated: true, identity: { sub: "admin", role: "admin" } });
});

