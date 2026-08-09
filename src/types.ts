export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type IncidentStatus = 'OPEN' | 'RESOLVED';
export type ClusterStatus = 'CONNECTED' | 'DISCONNECTED' | 'DEGRADED' | 'STUB';
export type NavTabType = 'overview' | 'incidents' | 'clusters' | 'nodes' | 'events';

export interface ResourceRef {
  kind: string;
  namespace: string;
  name: string;
  uid: string;
  labels?: Record<string, string>;
  owner_references?: Array<{
    kind: string;
    name: string;
    uid: string;
  }>;
}

export interface Diagnosis {
  category: string;
  severity: SeverityLevel;
  confidence: number;
  reason: string;
  root_cause: string;
  actionable_recommendation: string;
  mitigation_command?: string;
  impact_assessment?: string;
}

export interface ContainerState {
  name: string;
  image: string;
  ready: boolean;
  restart_count: number;
  state_type: 'waiting' | 'terminated' | 'running';
  reason?: string;
  message?: string;
  exit_code?: number;
}

export interface InvestigationEvidence {
  pod_phase?: string;
  node_name?: string;
  pod_ip?: string;
  container_states?: ContainerState[];
  kubernetes_events?: Array<{
    type: string;
    reason: string;
    message: string;
    count: number;
    last_timestamp: string;
  }>;
  recent_logs?: string[];
  metrics_summary?: {
    cpu_usage_mcores?: number;
    memory_usage_mb?: number;
    memory_limit_mb?: number;
  };
}

export interface AIAnalysis {
  status: 'COMPLETED' | 'PENDING' | 'FAILED';
  summary?: string;
  detailed_explanation?: string;
  probable_causes?: string[];
  remediation_steps?: string[];
  suggested_kubectl?: string[];
  analyzed_at?: string;
}

export interface Incident {
  id?: number;
  cluster_id: string;
  incident_id: string;
  resource: ResourceRef;
  category: string;
  status: IncidentStatus;
  current_state: string;
  severity: SeverityLevel;
  occurrences: number;
  first_seen: string;
  last_seen: string;
  resolved_at?: string | null;
  diagnosis?: Diagnosis | Record<string, any>;
  investigation?: InvestigationEvidence | Record<string, any>;
  ai_analysis?: AIAnalysis | Record<string, any>;
  state_history?: string[];
}

export interface ClusterInfo {
  cluster_id: string;
  name: string;
  status: ClusterStatus;
  kubernetes_version: string;
  node_count: number;
  pod_count: number;
  namespace_count: number;
  agent_status?: string;
  last_heartbeat?: string;
}

export interface K8sNode {
  name: string;
  status: 'Ready' | 'NotReady';
  role: string;
  version: string;
  cpu_cores: number;
  memory_gb: number;
  cpu_usage_pct: number;
  mem_usage_pct: number;
  pod_count: number;
}

export interface FilterOptions {
  searchQuery: string;
  clusterId: string;
  severity: SeverityLevel | 'ALL';
  status: IncidentStatus | 'ALL';
  category: string;
  namespace: string;
}
