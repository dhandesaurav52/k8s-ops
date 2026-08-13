import { Router, Request, Response } from 'express';

export const fallbackRouter = Router();

// Health check
fallbackRouter.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'healthy', service: 'SkyOps Express Fallback Server', version: '1.0.0' });
});

// Clusters
fallbackRouter.get('/clusters', (req: Request, res: Response) => {
  res.json([]);
});

fallbackRouter.get('/clusters/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  res.status(404).json({ detail: `Cluster '${id}' not found` });
});

// Default Metrics Data
const getDefaultMetrics = (cid: string) => {
  const nowIso = new Date().toISOString();
  return {
    cluster_id: cid,
    metrics_status: 'UNAVAILABLE',
    status_message: 'No live metrics reported by SkyOps agent yet',
    source: 'metrics.k8s.io',
    last_collected: nowIso,
    summary: {
      total_cpu_mcores: 0,
      used_cpu_mcores: 0,
      cpu_utilization_pct: 0,
      total_memory_mb: 0,
      used_memory_mb: 0,
      memory_utilization_pct: 0,
    },
    nodes: [],
    pods: [],
  };
};

// Metrics
fallbackRouter.get('/metrics', (req: Request, res: Response) => {
  const cid = (req.query.cluster_id as string) || 'none';
  res.json(getDefaultMetrics(cid));
});

fallbackRouter.get('/metrics/nodes', (req: Request, res: Response) => {
  res.json([]);
});

fallbackRouter.get('/metrics/pods', (req: Request, res: Response) => {
  res.json([]);
});

fallbackRouter.get('/metrics/history', (req: Request, res: Response) => {
  const cid = (req.query.cluster_id as string) || 'none';
  const range = (req.query.range as string) || '1h';

  res.json({
    cluster_id: cid,
    time_range: range,
    metrics_status: 'UNAVAILABLE',
    points: [],
  });
});

// Incidents in-memory store
const inMemoryIncidents: any[] = [];

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
    is_setup_completed: true,
    authenticated: true,
    user: { username: "admin", role: "admin", email: "admin@skyops.internal" },
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

