import {
  ClusterInfo,
  ClusterMetricSummary,
  Incident,
  IncidentStatus,
  MetricHistoryResponse,
  NodeMetric,
  PodMetric,
  SeverityLevel,
} from '../types';

const API_BASE = (((import.meta as any).env?.VITE_SKYOPS_API_URL as string) || '').replace(/\/$/, '');

const getStoredToken = (): string => {
  try {
    if (typeof localStorage !== 'undefined') {
      return localStorage.getItem('skyops_token') || 'skyops-agent-secret-token';
    }
  } catch {
    // Ignore restricted storage contexts
  }
  return 'skyops-agent-secret-token';
};

class ApiService {
  private authToken: string = getStoredToken();

  setAuthToken(token: string) {
    this.authToken = token;
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('skyops_token', token);
      }
    } catch {
      // Ignore storage restrictions
    }
  }

  getAuthToken(): string {
    return this.authToken;
  }

  async getAuthStatus(): Promise<{ is_setup_completed: boolean; authenticated: boolean; user: { username: string; role: string; email?: string } | null }> {
    try {
      const res = await this.requestWithRetry(this.getUrl('/api/v1/auth/status'), {
        headers: { Accept: 'application/json' },
      }, 5000, 1);
      if (!res.ok) {
        return { is_setup_completed: false, authenticated: false, user: null };
      }
      return await this.safeJson(res);
    } catch {
      return { is_setup_completed: false, authenticated: false, user: null };
    }
  }

  async verifyInitialPassword(initialPassword: string): Promise<{ status: string; message: string }> {
    const res = await this.requestWithRetry(this.getUrl('/api/v1/auth/verify-initial-password'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initial_password: initialPassword }),
    });
    if (!res.ok) {
      const err = await this.safeJson<{ detail?: string }>(res).catch(() => ({ detail: 'Invalid initial password' }));
      throw new Error(err.detail || 'Invalid initial administrator password');
    }
    return await this.safeJson(res);
  }

  async setupAdmin(data: { initial_password: string; username: string; email?: string; password: string }): Promise<{ status: string; message: string }> {
    const res = await this.requestWithRetry(this.getUrl('/api/v1/auth/setup-admin'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await this.safeJson<{ detail?: string }>(res).catch(() => ({ detail: 'Setup failed' }));
      throw new Error(err.detail || 'Failed to complete initial administrator setup');
    }
    return await this.safeJson(res);
  }

  async login(username: string, password: string) {
    const res = await this.requestWithRetry(this.getUrl('/api/v1/auth/login'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const err = await this.safeJson<{ detail?: string }>(res).catch(() => ({ detail: 'Invalid credentials' }));
      throw new Error(err.detail || 'Invalid username or password');
    }
    const data = await this.safeJson<any>(res);
    if (data.token) {
      this.setAuthToken(data.token);
    }
    return data;
  }

  async logout(): Promise<void> {
    try {
      await this.requestWithRetry(this.getUrl('/api/v1/auth/logout'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
    } catch {
      // ignore
    }
    this.setAuthToken('');
  }

  private async safeJson<T = any>(res: Response): Promise<T> {
    const text = await res.text();
    if (text.trim().startsWith('<')) {
      throw new Error(`Server returned HTML instead of JSON (HTTP ${res.status}). Check backend routing.`);
    }
    try {
      return JSON.parse(text) as T;
    } catch {
      throw new Error(`Server returned non-JSON response (HTTP ${res.status}): ${text.slice(0, 120)}`);
    }
  }

  private getUrl(endpoint: string): string {
    return `${API_BASE}${endpoint}`;
  }

  private async requestWithRetry(
    url: string,
    init: RequestInit = {},
    timeoutMs = 12000,
    retries = 1
  ): Promise<Response> {
    let lastError: any;
    const reqHeaders = new Headers(init.headers || {});
    if (!reqHeaders.has('Authorization') && this.authToken) {
      reqHeaders.set('Authorization', `Bearer ${this.authToken}`);
    }

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeoutMs);
        const res = await fetch(url, { ...init, headers: reqHeaders, credentials: 'include', signal: controller.signal });
        clearTimeout(timer);
        return res;
      } catch (e: any) {
        lastError = e;
        if (attempt < retries) {
          await new Promise((resolve) => setTimeout(resolve, 400));
        }
      }
    }
    if (
      lastError?.name === 'AbortError' ||
      lastError?.message?.includes('timed out') ||
      lastError?.message?.includes('aborted')
    ) {
      throw new Error('SkyOps Server request timed out');
    }
    throw lastError;
  }

  /**
   * Ping backend health endpoint and return live latency, status and timestamp.
   */
  async checkHealth(): Promise<{ status: 'CONNECTED' | 'DEGRADED' | 'OFFLINE'; latencyMs: number; timestamp: string }> {
    const start = performance.now();
    try {
      const res = await this.requestWithRetry(this.getUrl('/api/v1/health'), {
        headers: { Accept: 'application/json' },
      }, 5000, 1);
      const duration = Math.round(performance.now() - start);
      if (res.ok) {
        return {
          status: duration > 1500 ? 'DEGRADED' : 'CONNECTED',
          latencyMs: duration,
          timestamp: new Date().toISOString(),
        };
      } else {
        return {
          status: 'DEGRADED',
          latencyMs: duration,
          timestamp: new Date().toISOString(),
        };
      }
    } catch {
      const duration = Math.round(performance.now() - start);
      return {
        status: 'OFFLINE',
        latencyMs: duration,
        timestamp: new Date().toISOString(),
      };
    }
  }

  /**
   * Fetch all registered Kubernetes clusters from SkyOps Server API.
   */
  async fetchClusters(): Promise<ClusterInfo[]> {
    const res = await this.requestWithRetry(this.getUrl('/api/v1/clusters'), {
      headers: { 'Accept': 'application/json' },
    }, 12000, 1);

    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`SkyOps API error (${res.status}): ${errText || res.statusText}`);
    }

    const data = await this.safeJson<any>(res);
    if (!Array.isArray(data)) {
      throw new Error('Invalid response format for clusters');
    }

    return data.map((c: any) => ({
      cluster_id: c.cluster_id || 'unknown',
      name: c.name || c.cluster_id,
      status: c.status || 'CONNECTED',
      kubernetes_version: c.kubernetes_version || 'v1.28.0',
      node_count: c.node_count ?? 0,
      pod_count: c.pod_count ?? 0,
      namespace_count: c.namespace_count ?? 0,
      agent_status: c.agent_status || 'HEALTHY',
      last_heartbeat: c.updated_at || c.last_seen || new Date().toISOString(),
    }));
  }

  /**
   * Fetch a single cluster by cluster_id.
   */
  async getCluster(clusterId: string): Promise<ClusterInfo | null> {
    const res = await this.requestWithRetry(this.getUrl(`/api/v1/clusters/${encodeURIComponent(clusterId)}`), {
      headers: { 'Accept': 'application/json' },
    }, 12000, 1);

    if (!res.ok) {
      if (res.status === 404) return null;
      throw new Error(`SkyOps API error (${res.status})`);
    }

    const c = await this.safeJson<any>(res);
    return {
      cluster_id: c.cluster_id || clusterId,
      name: c.name || c.cluster_id,
      status: c.status || 'CONNECTED',
      kubernetes_version: c.kubernetes_version || 'v1.28.0',
      node_count: c.node_count ?? 0,
      pod_count: c.pod_count ?? 0,
      namespace_count: c.namespace_count ?? 0,
      agent_status: c.agent_status || 'HEALTHY',
      last_heartbeat: c.updated_at || c.last_seen || new Date().toISOString(),
    };
  }

  /**
   * Fetch incidents from SkyOps Server API with optional cluster and status filtering.
   */
  async fetchIncidents(clusterId?: string, status?: string): Promise<Incident[]> {
    let endpoint = '/api/v1/incidents';
    const params = new URLSearchParams();
    if (clusterId && clusterId !== 'ALL') params.append('cluster_id', clusterId);
    if (status && status !== 'ALL') params.append('status', status);
    if (params.toString()) endpoint += `?${params.toString()}`;

    const res = await this.requestWithRetry(this.getUrl(endpoint), {
      headers: { 'Accept': 'application/json' },
    }, 12000, 1);

    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`SkyOps API error (${res.status}): ${errText || res.statusText}`);
    }

    const data = await this.safeJson<any>(res);
    if (!Array.isArray(data)) {
      throw new Error('Invalid response format for incidents');
    }

    return data.filter(Boolean).map((item: any) => ({
      id: item.id || 0,
      cluster_id: item.cluster_id || 'unknown',
      incident_id: item.incident_id || `INC-${item.id || '000'}`,
      category: item.category || 'UNKNOWN',
      status: (item.status || 'OPEN') as IncidentStatus,
      current_state: item.current_state || '',
      severity: (item.severity || 'MEDIUM') as SeverityLevel,
      occurrences: item.occurrences || 1,
      first_seen: item.first_seen || item.created_at || new Date().toISOString(),
      last_seen: item.last_seen || item.updated_at || new Date().toISOString(),
      resolved_at: item.resolved_at || null,
      resource: {
        kind: item.resource_kind || item.resource?.kind || 'Pod',
        namespace: item.resource_namespace || item.resource?.namespace || 'default',
        name: item.resource_name || item.resource?.name || 'unknown',
        uid: item.resource_uid || item.resource?.uid || `uid-${item.incident_id || '000'}`,
        labels: item.resource?.labels || {},
        owner_references: item.resource?.owner_references || [],
      },
      diagnosis: typeof item.diagnosis === 'object' && item.diagnosis !== null ? item.diagnosis : {},
      investigation: typeof item.investigation === 'object' && item.investigation !== null ? item.investigation : {},
      ai_analysis: typeof item.ai_analysis === 'object' && item.ai_analysis !== null ? item.ai_analysis : {},
      state_history: Array.isArray(item.state_history) ? item.state_history : [],
    }));
  }

  /**
   * Retrieve a single incident by database ID or string incident_id.
   */
  async getIncident(incidentId: string, clusterId?: string): Promise<Incident | null> {
    let endpoint = `/api/v1/incidents/${encodeURIComponent(incidentId)}`;
    if (clusterId && clusterId !== 'ALL') endpoint += `?cluster_id=${encodeURIComponent(clusterId)}`;

    const res = await this.requestWithRetry(this.getUrl(endpoint), {
      headers: { 'Accept': 'application/json' },
    }, 12000, 1);

    if (!res.ok) {
      if (res.status === 404) return null;
      throw new Error(`SkyOps API error: ${res.status}`);
    }

    const item = await this.safeJson<any>(res);
    return {
      id: item.id || 0,
      cluster_id: item.cluster_id || 'unknown',
      incident_id: item.incident_id || `INC-${item.id || '000'}`,
      category: item.category || 'UNKNOWN',
      status: (item.status || 'OPEN') as IncidentStatus,
      current_state: item.current_state || '',
      severity: (item.severity || 'MEDIUM') as SeverityLevel,
      occurrences: item.occurrences || 1,
      first_seen: item.first_seen || item.created_at || new Date().toISOString(),
      last_seen: item.last_seen || item.updated_at || new Date().toISOString(),
      resolved_at: item.resolved_at || null,
      resource: {
        kind: item.resource_kind || item.resource?.kind || 'Pod',
        namespace: item.resource_namespace || item.resource?.namespace || 'default',
        name: item.resource_name || item.resource?.name || 'unknown',
        uid: item.resource_uid || item.resource?.uid || `uid-${item.incident_id || '000'}`,
        labels: item.resource?.labels || {},
        owner_references: item.resource?.owner_references || [],
      },
      diagnosis: typeof item.diagnosis === 'object' && item.diagnosis !== null ? item.diagnosis : {},
      investigation: typeof item.investigation === 'object' && item.investigation !== null ? item.investigation : {},
      ai_analysis: typeof item.ai_analysis === 'object' && item.ai_analysis !== null ? item.ai_analysis : {},
      state_history: Array.isArray(item.state_history) ? item.state_history : [],
    };
  }

  /**
   * Mark an incident as RESOLVED via the SkyOps Cloud Backend API.
   */
  async resolveIncident(incidentId: string): Promise<boolean> {
    const res = await this.requestWithRetry(this.getUrl(`/api/v1/incidents/${encodeURIComponent(incidentId)}/resolve`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }, 12000, 1);

    if (!res.ok) {
      throw new Error(`Failed to resolve incident '${incidentId}': HTTP ${res.status}`);
    }

    return true;
  }

  /**
   * Inject a real incident simulation via POST /api/v1/incidents.
   */
  async injectSimulationIncident(scenario: 'OOM' | 'IMAGE_PULL' | 'CRASH_LOOP' | 'PVC_PENDING'): Promise<Incident> {
    const nextNum = Math.floor(1000 + Math.random() * 9000);
    const incidentId = `INC-${nextNum}`;
    const now = new Date().toISOString();

    let payload: any;

    if (scenario === 'OOM') {
      payload = {
        cluster_id: 'skyops-cluster-prod-us',
        incident_id: incidentId,
        category: 'OOMKilled',
        status: 'OPEN',
        severity: 'CRITICAL',
        current_state: 'payment-api: OOMKilled (Exit code 137, Restarts: 4)',
        occurrences: 4,
        resource_kind: 'Pod',
        resource_namespace: 'payments',
        resource_name: `payment-api-worker-${nextNum}`,
        resource_uid: `uid-pod-${nextNum}`,
        diagnosis: {
          category: 'OOMKilled',
          severity: 'CRITICAL',
          confidence: 0.95,
          reason: 'Process cgroup RSS memory limit exceeded',
          root_cause: `Container payment-api hit memory limit 256Mi during payload processing. SIGKILL triggered by cgroup manager.`,
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
            { type: 'Warning', reason: 'OOMKilling', message: 'Memory cgroup out of memory: Killed process pid=19420 (node)', count: 4, last_timestamp: now },
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
          suggested_kubectl: [`kubectl describe pod payment-api-worker-${nextNum} -n payments`],
          analyzed_at: now,
        },
        state_history: ['Pending', 'Running', 'OOMKilled'],
      };
    } else if (scenario === 'IMAGE_PULL') {
      payload = {
        cluster_id: 'skyops-cluster-staging-eu',
        incident_id: incidentId,
        category: 'ImagePullFailure',
        status: 'OPEN',
        severity: 'HIGH',
        current_state: 'catalog-service: ErrImagePull (manifest unknown)',
        occurrences: 3,
        resource_kind: 'Pod',
        resource_namespace: 'catalog',
        resource_name: `catalog-svc-${nextNum}`,
        resource_uid: `uid-cat-${nextNum}`,
        diagnosis: {
          category: 'ImagePullFailure',
          severity: 'HIGH',
          confidence: 0.98,
          reason: 'Container registry image tag not found',
          root_cause: `The registry returned HTTP 404 for image tag v4.0.1-nightly.`,
          actionable_recommendation: 'Revert deployment container image tag to v4.0.0 stable.',
          mitigation_command: `kubectl set image deployment/catalog-service catalog=registry.internal.net/catalog:v4.0.0 -n catalog`,
        },
        investigation: {
          pod_phase: 'Pending',
          node_name: 'staging-worker-01',
          pod_ip: '10.244.1.88',
          container_states: [
            {
              name: 'catalog',
              image: 'registry.internal.net/catalog:v4.0.1-nightly',
              ready: false,
              restart_count: 0,
              state_type: 'waiting',
              reason: 'ImagePullBackOff',
              message: 'Back-off pulling image',
            },
          ],
          kubernetes_events: [
            { type: 'Warning', reason: 'Failed', message: 'Failed to pull image: manifest unknown', count: 3, last_timestamp: now },
          ],
          recent_logs: [],
          metrics_summary: { cpu_usage_mcores: 0, memory_usage_mb: 0, memory_limit_mb: 256 },
        },
        ai_analysis: {
          status: 'COMPLETED',
          summary: 'Image pull error blocking catalog pod initialization.',
          detailed_explanation: 'Image tag v4.0.1-nightly was requested but manifest unknown was returned by artifact registry.',
          probable_causes: ['Nightly build failed to push to registry', 'Typo in Helm release tag'],
          remediation_steps: ['Verify tag existence in registry', 'Rollback deployment to stable tag v4.0.0'],
          suggested_kubectl: [`kubectl rollout undo deployment/catalog-service -n catalog`],
          analyzed_at: now,
        },
        state_history: ['Pending', 'ErrImagePull', 'ImagePullBackOff'],
      };
    } else if (scenario === 'PVC_PENDING') {
      payload = {
        cluster_id: 'skyops-cluster-prod-us',
        incident_id: incidentId,
        category: 'VolumeMountFailure',
        status: 'OPEN',
        severity: 'HIGH',
        current_state: 'postgres-db-0: VolumeBindingWaiting (PVC data-postgres-db-0 unbound)',
        occurrences: 5,
        resource_kind: 'Pod',
        resource_namespace: 'database',
        resource_name: 'postgres-db-0',
        resource_uid: `uid-pg-${nextNum}`,
        diagnosis: {
          category: 'VolumeMountFailure',
          severity: 'HIGH',
          confidence: 0.92,
          reason: 'StorageClass cloud volume quota or zone constraint failure',
          root_cause: `PersistentVolumeClaim data-postgres-db-0 in namespace database cannot be bound. StorageClass pd-ssd is unable to provision 500Gi volume in zone us-east1-a due to storage account quota limit.`,
          actionable_recommendation: 'Request storage quota extension in GCP console or modify PVC request size.',
          mitigation_command: `kubectl describe pvc data-postgres-db-0 -n database`,
        },
        investigation: {
          pod_phase: 'Pending',
          node_name: 'gke-prod-pool-1-8a9d01',
          container_states: [],
          kubernetes_events: [
            { type: 'Warning', reason: 'FailedScheduling', message: '0/8 nodes are available: unbound immediate PersistentVolumeClaims.', count: 5, last_timestamp: now },
          ],
          recent_logs: [],
        },
        ai_analysis: {
          status: 'COMPLETED',
          summary: 'PersistentVolumeClaim binding failure preventing database pod scheduling.',
          detailed_explanation: 'Kubernetes scheduler cannot bind PVC data-postgres-db-0 because cloud CSI driver returned quota exceeded error.',
          probable_causes: ['Cloud disk quota exceeded in region us-east1', 'Zone topology constraint on StorageClass'],
          remediation_steps: ['Increase cloud persistent disk quota', 'Check StorageClass volumeBindingMode'],
          suggested_kubectl: [`kubectl get pvc -n database`, `kubectl describe storageclass pd-ssd`],
          analyzed_at: now,
        },
        state_history: ['Pending', 'FailedScheduling'],
      };
    } else {
      payload = {
        cluster_id: 'skyops-cluster-staging-eu',
        incident_id: incidentId,
        category: 'CrashLoopBackOff',
        status: 'OPEN',
        severity: 'MEDIUM',
        current_state: 'worker-node-job: CrashLoopBackOff (Exit Code 1)',
        occurrences: 8,
        resource_kind: 'Pod',
        resource_namespace: 'jobs',
        resource_name: `data-exporter-${nextNum}`,
        resource_uid: `uid-job-${nextNum}`,
        diagnosis: {
          category: 'CrashLoopBackOff',
          severity: 'MEDIUM',
          confidence: 0.91,
          reason: 'Database authentication failed',
          root_cause: 'Data exporter container exited with code 1. Error: ConnectionRefusedError connecting to postgresql://db.internal:5432/analytics.',
          actionable_recommendation: 'Check Secret db-credentials in namespace jobs and verify database network security group.',
          mitigation_command: `kubectl get secret db-credentials -n jobs -o yaml`,
        },
        investigation: {
          pod_phase: 'Running',
          node_name: 'staging-worker-01',
          container_states: [
            {
              name: 'exporter',
              image: 'registry.internal.net/jobs/exporter:v1.2.0',
              ready: false,
              restart_count: 8,
              state_type: 'waiting',
              reason: 'CrashLoopBackOff',
            },
          ],
          kubernetes_events: [
            { type: 'Warning', reason: 'BackOff', message: 'Back-off restarting failed container', count: 12, last_timestamp: now },
          ],
          recent_logs: [
            'Connecting to postgresql://db.internal:5432/analytics...',
            'Fatal: Connection refused on port 5432',
          ],
        },
        ai_analysis: {
          status: 'COMPLETED',
          summary: 'Database connection failure triggering container CrashLoopBackOff.',
          detailed_explanation: 'Exporter service is unable to establish TCP handshake with analytics DB host.',
          probable_causes: ['Database host down or unreachable', 'Incorrect password in Secret db-credentials'],
          remediation_steps: ['Test database TCP connectivity using nc/telnet', 'Verify secret values'],
          suggested_kubectl: [`kubectl logs data-exporter-${nextNum} -n jobs`],
          analyzed_at: now,
        },
        state_history: ['Pending', 'Running', 'Terminated', 'CrashLoopBackOff'],
      };
    }

    const res = await this.requestWithRetry(this.getUrl('/api/v1/incidents'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, 12000, 1);

    if (!res.ok) {
      throw new Error(`Failed to inject simulation incident: HTTP ${res.status}`);
    }

    const item = await this.safeJson<any>(res);
    return {
      id: item.id,
      cluster_id: item.cluster_id,
      incident_id: item.incident_id,
      category: item.category,
      status: (item.status || 'OPEN') as IncidentStatus,
      current_state: item.current_state || '',
      severity: (item.severity || 'MEDIUM') as SeverityLevel,
      occurrences: item.occurrences || 1,
      first_seen: item.first_seen || item.created_at || now,
      last_seen: item.last_seen || item.updated_at || now,
      resolved_at: item.resolved_at || null,
      resource: {
        kind: item.resource_kind || 'Pod',
        namespace: item.resource_namespace || 'default',
        name: item.resource_name || 'unknown',
        uid: item.resource_uid || `uid-${item.incident_id}`,
      },
      diagnosis: item.diagnosis || {},
      investigation: item.investigation || {},
      ai_analysis: item.ai_analysis || {},
      state_history: item.state_history || [],
    };
  }

  /**
   * Fetch resource metrics summary for a specific cluster.
   */
  async fetchMetricsSummary(clusterId?: string): Promise<ClusterMetricSummary> {
    let endpoint = '/api/v1/metrics';
    if (clusterId && clusterId !== 'ALL') {
      endpoint += `?cluster_id=${encodeURIComponent(clusterId)}`;
    }

    const res = await this.requestWithRetry(this.getUrl(endpoint), {
      headers: { Accept: 'application/json' },
    }, 12000, 1);

    if (!res.ok) {
      throw new Error(`Metrics API error: ${res.status}`);
    }

    return await this.safeJson<ClusterMetricSummary>(res);
  }

  /**
   * Fetch node metrics for cluster(s).
   */
  async fetchNodeMetrics(clusterId?: string): Promise<NodeMetric[]> {
    let endpoint = '/api/v1/metrics/nodes';
    if (clusterId && clusterId !== 'ALL') {
      endpoint += `?cluster_id=${encodeURIComponent(clusterId)}`;
    }

    const res = await this.requestWithRetry(this.getUrl(endpoint), {
      headers: { Accept: 'application/json' },
    }, 12000, 1);

    if (!res.ok) {
      throw new Error(`Node Metrics API error: ${res.status}`);
    }

    return await this.safeJson<NodeMetric[]>(res);
  }

  /**
   * Fetch pod metrics for cluster(s).
   */
  async fetchPodMetrics(clusterId?: string): Promise<PodMetric[]> {
    let endpoint = '/api/v1/metrics/pods';
    if (clusterId && clusterId !== 'ALL') {
      endpoint += `?cluster_id=${encodeURIComponent(clusterId)}`;
    }

    const res = await this.requestWithRetry(this.getUrl(endpoint), {
      headers: { Accept: 'application/json' },
    }, 12000, 1);

    if (!res.ok) {
      throw new Error(`Pod Metrics API error: ${res.status}`);
    }

    return await this.safeJson<PodMetric[]>(res);
  }

  /**
   * Fetch historical metrics time-series points.
   */
  async fetchMetricHistory(clusterId?: string, range: string = '1h'): Promise<MetricHistoryResponse> {
    let endpoint = `/api/v1/metrics/history?range=${encodeURIComponent(range)}`;
    if (clusterId && clusterId !== 'ALL') {
      endpoint += `&cluster_id=${encodeURIComponent(clusterId)}`;
    }

    const res = await this.requestWithRetry(this.getUrl(endpoint), {
      headers: { Accept: 'application/json' },
    }, 12000, 1);

    if (!res.ok) {
      throw new Error(`Metric History API error: ${res.status}`);
    }

    return await this.safeJson<MetricHistoryResponse>(res);
  }

  /**
   * List remediation plans.
   */
  async listRemediations(clusterId?: string, incidentId?: string): Promise<any[]> {
    let endpoint = '/api/v1/remediations';
    const params = new URLSearchParams();
    if (clusterId && clusterId !== 'ALL') params.append('cluster_id', clusterId);
    if (incidentId) params.append('incident_id', incidentId);
    if (params.toString()) endpoint += `?${params.toString()}`;

    const res = await this.requestWithRetry(this.getUrl(endpoint), {
      headers: { Accept: 'application/json' },
    }, 12000, 1);

    if (!res.ok) {
      throw new Error(`Remediations API error: ${res.status}`);
    }

    return await this.safeJson<any[]>(res);
  }

  /**
   * Get specific remediation details.
   */
  async getRemediation(id: string): Promise<any> {
    const res = await this.requestWithRetry(this.getUrl(`/api/v1/remediations/${encodeURIComponent(id)}`), {
      headers: { Accept: 'application/json' },
    }, 12000, 1);

    if (!res.ok) {
      if (res.status === 404) return null;
      throw new Error(`Remediation API error: ${res.status}`);
    }

    return await this.safeJson<any>(res);
  }

  /**
   * Trigger dry-run validation for a remediation plan.
   */
  async dryRunRemediation(id: string): Promise<any> {
    const res = await this.requestWithRetry(this.getUrl(`/api/v1/remediations/${encodeURIComponent(id)}/dry-run`), {
      method: 'POST',
      headers: { Accept: 'application/json' },
    }, 12000, 1);

    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`Dry Run error (${res.status}): ${errText || res.statusText}`);
    }

    return await this.safeJson<any>(res);
  }

  /**
   * Approve a remediation plan.
   */
  async approveRemediation(id: string, approvedBy = 'operator@skyops.internal'): Promise<any> {
    const res = await this.requestWithRetry(this.getUrl(`/api/v1/remediations/${encodeURIComponent(id)}/approve`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ approved_by: approvedBy }),
    }, 12000, 1);

    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`Approve error (${res.status}): ${errText || res.statusText}`);
    }

    return await this.safeJson<any>(res);
  }

  /**
   * Reject a remediation plan.
   */
  async rejectRemediation(id: string, rejectedBy = 'operator@skyops.internal', reason = 'Rejected by operator'): Promise<any> {
    const res = await this.requestWithRetry(this.getUrl(`/api/v1/remediations/${encodeURIComponent(id)}/reject`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ rejected_by: rejectedBy, reason }),
    }, 12000, 1);

    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`Reject error (${res.status}): ${errText || res.statusText}`);
    }

    return await this.safeJson<any>(res);
  }

  /**
   * Execute an approved remediation plan.
   */
  async executeRemediation(id: string): Promise<any> {
    const res = await this.requestWithRetry(this.getUrl(`/api/v1/remediations/${encodeURIComponent(id)}/execute`), {
      method: 'POST',
      headers: { Accept: 'application/json' },
    }, 12000, 1);

    if (!res.ok) {
      const errJson = await this.safeJson<any>(res).catch(() => null);
      const detail = errJson?.detail || `HTTP ${res.status}`;
      throw new Error(`Execute error: ${detail}`);
    }

    return await this.safeJson<any>(res);
  }

  /**
   * Fetch audit records.
   */
  async fetchAuditRecords(clusterId?: string): Promise<any[]> {
    let endpoint = '/api/v1/remediations/audit';
    if (clusterId && clusterId !== 'ALL') {
      endpoint += `?cluster_id=${encodeURIComponent(clusterId)}`;
    }

    const res = await this.requestWithRetry(this.getUrl(endpoint), {
      headers: { Accept: 'application/json' },
    }, 12000, 1);

    if (!res.ok) {
      return [];
    }

    return await this.safeJson<any[]>(res);
  }
}

export const apiService = new ApiService();
