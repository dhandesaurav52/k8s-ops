export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type IncidentStatus = 'OPEN' | 'RESOLVED';
export type ClusterStatus = 'CONNECTED' | 'DISCONNECTED' | 'DEGRADED' | 'STUB';
export type NavTabType = 'overview' | 'incidents' | 'metrics' | 'clusters' | 'nodes' | 'events';

export type MetricsStatus = 'ONLINE' | 'DEGRADED' | 'UNAVAILABLE';

export interface NodeMetric {
  name: string;
  cluster_id: string;
  cpu_usage_mcores: number;
  cpu_capacity_mcores: number;
  cpu_pct: number;
  memory_usage_mb: number;
  memory_capacity_mb: number;
  memory_pct: number;
  status: 'Ready' | 'NotReady';
  conditions?: Record<string, string>;
}

export interface PodMetric {
  name: string;
  namespace: string;
  cluster_id: string;
  node_name?: string;
  cpu_usage_mcores: number;
  memory_usage_mb: number;
  restarts?: number;
  phase?: string;
}

export interface ClusterMetricSummary {
  cluster_id: string;
  metrics_status: MetricsStatus;
  status_message: string;
  source: string;
  last_collected: string;
  summary: {
    total_cpu_mcores: number;
    used_cpu_mcores: number;
    cpu_utilization_pct: number;
    total_memory_mb: number;
    used_memory_mb: number;
    memory_utilization_pct: number;
  };
  nodes: NodeMetric[];
  pods: PodMetric[];
}

export interface MetricHistoryPoint {
  timestamp: string;
  timeLabel: string;
  cpu_pct: number;
  memory_pct: number;
  cpu_mcores: number;
  memory_mb: number;
}

export interface MetricHistoryResponse {
  cluster_id: string;
  time_range: string;
  metrics_status: MetricsStatus;
  points: MetricHistoryPoint[];
}

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

export interface TimelineEvidenceItem {
  evidence_id: string;
  incident_id: string;
  source: 'KUBERNETES_EVENT' | 'CONTAINER_STATE' | 'POD_STATE' | 'LOG' | 'METRIC' | 'NODE_STATE' | 'WORKLOAD_STATE' | 'STATE_TRANSITION';
  resource: string;
  timestamp: string;
  signal_type: string;
  observation: string;
  relevance: 'HIGH' | 'MEDIUM' | 'LOW';
  raw_reference?: Record<string, any>;
}

export interface BlastRadiusInfo {
  scope_level: 'CONTAINER' | 'POD' | 'WORKLOAD' | 'NAMESPACE' | 'NODE' | 'CLUSTER';
  summary: string;
  impacted_resources: Array<{
    kind: string;
    name: string;
    namespace: string;
    status: string;
  }>;
  workload_status?: {
    kind?: string;
    name?: string;
    desired_replicas?: number;
    ready_replicas?: number;
    affected_replicas?: number;
  };
  service_status?: Array<{
    name: string;
    namespace: string;
    ready_endpoints: number;
    total_endpoints: number;
  }>;
}

export interface RelatedIncidentInfo {
  incident_id: string;
  resource_name: string;
  namespace: string;
  category: string;
  relationship_type: 'SAME_RESOURCE' | 'RELATED_RESOURCE' | 'SIMILAR_INCIDENT';
  created_at: string;
  status: string;
}

export interface RootCauseAnalysisInfo {
  candidate_root_cause: string;
  confidence_score: number;
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW';
  confidence_reasoning: string;
  supporting_evidence: Array<Record<string, any>>;
  contradicting_evidence: Array<Record<string, any>>;
  impacted_resources: string[];
  recommended_actions: string[];
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
  evidence_timeline?: TimelineEvidenceItem[];
  root_cause_analysis?: RootCauseAnalysisInfo;
  blast_radius?: BlastRadiusInfo;
  related_incidents?: RelatedIncidentInfo[];
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
  cluster_id?: string;
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
