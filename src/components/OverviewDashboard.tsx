import React from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Layers,
  Radio,
  Server,
  ShieldAlert,
  Clock,
  ArrowRight,
  Activity,
  Terminal,
} from 'lucide-react';
import { ClusterInfo, Incident, NavTabType } from '../types';
import { SeverityBadge, StatusBadge } from './IncidentStatusBadge';

interface OverviewDashboardProps {
  clusters: ClusterInfo[];
  incidents: Incident[];
  selectedClusterId: string;
  onSelectIncident: (incident: Incident) => void;
  onNavigateTab: (tab: NavTabType) => void;
  onSelectCluster: (clusterId: string) => void;
}

export const OverviewDashboard: React.FC<OverviewDashboardProps> = ({
  clusters,
  incidents,
  selectedClusterId,
  onSelectIncident,
  onNavigateTab,
  onSelectCluster,
}) => {
  // Filter data according to global selectedClusterId scope
  const isGlobalAll = !selectedClusterId || selectedClusterId === 'ALL';
  const scopedClusters = isGlobalAll
    ? clusters
    : clusters.filter((c) => c.cluster_id === selectedClusterId);
  const scopedIncidents = isGlobalAll
    ? incidents
    : incidents.filter((i) => i.cluster_id === selectedClusterId);

  // Calculated live metrics for current scope
  const totalClusters = scopedClusters.length;
  const connectedClusters = scopedClusters.filter((c) => c.status === 'CONNECTED' || c.status === 'STUB').length;
  const degradedClusters = scopedClusters.filter((c) => c.status === 'DEGRADED').length;
  const offlineClusters = scopedClusters.filter((c) => c.status === 'DISCONNECTED').length;

  const openIncidents = scopedIncidents.filter((i) => i.status === 'OPEN');
  const criticalIncidents = openIncidents.filter((i) => i.severity === 'CRITICAL');
  const highIncidents = openIncidents.filter((i) => i.severity === 'HIGH');
  const mediumIncidents = openIncidents.filter((i) => i.severity === 'MEDIUM');
  const lowIncidents = openIncidents.filter((i) => i.severity === 'LOW');
  const resolvedIncidents = scopedIncidents.filter((i) => i.status === 'RESOLVED');

  const totalNodes = scopedClusters.reduce((acc, c) => acc + (c.node_count || 0), 0);
  const totalPods = scopedClusters.reduce((acc, c) => acc + (c.pod_count || 0), 0);
  const totalNamespaces = scopedClusters.reduce((acc, c) => acc + (c.namespace_count || 0), 0);

  const healthyAgents = scopedClusters.filter((c) => c.agent_status === 'HEALTHY' || c.agent_status === 'LOCAL_DEV').length;

  const recentIncidents = [...scopedIncidents]
    .sort((a, b) => new Date(b.last_seen).getTime() - new Date(a.last_seen).getTime())
    .slice(0, 5);

  const formatRelativeTime = (isoString: string) => {
    try {
      const diffMs = Date.now() - new Date(isoString).getTime();
      const mins = Math.floor(diffMs / (1000 * 60));
      if (mins < 1) return 'just now';
      if (mins < 60) return `${mins}m ago`;
      const hours = Math.floor(mins / 60);
      if (hours < 24) return `${hours}h ago`;
      return `${Math.floor(hours / 24)}d ago`;
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-4 font-mono text-xs text-neutral-200">
      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Card 1: Clusters */}
        <div className="bg-neutral-900 border border-neutral-800 p-3.5 rounded shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between text-[11px] text-neutral-400 font-semibold mb-1">
            <span>CLUSTERS SCOPE</span>
            <Server className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-neutral-100 mb-2">{totalClusters}</div>
          <div className="flex items-center gap-3 text-[11px] border-t border-neutral-800/80 pt-2 text-neutral-400">
            <span className="text-emerald-400 font-semibold">{connectedClusters} Connected</span>
            {degradedClusters > 0 && <span className="text-amber-400">{degradedClusters} Degraded</span>}
            {offlineClusters > 0 && <span className="text-red-400">{offlineClusters} Offline</span>}
          </div>
        </div>

        {/* Card 2: Open Incidents */}
        <div
          onClick={() => onNavigateTab('incidents')}
          className="bg-neutral-900 border border-neutral-800 hover:border-neutral-700 p-3.5 rounded shadow-lg cursor-pointer transition-all"
        >
          <div className="flex items-center justify-between text-[11px] text-neutral-400 font-semibold mb-1">
            <span>OPEN INCIDENTS</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-2xl font-bold text-amber-400">{openIncidents.length}</span>
            {criticalIncidents.length > 0 && (
              <span className="px-1.5 py-0.5 bg-red-950 text-red-400 border border-red-800 rounded font-bold text-[10px] animate-pulse">
                {criticalIncidents.length} CRITICAL
              </span>
            )}
          </div>
          <div className="flex items-center justify-between text-[11px] border-t border-neutral-800/80 pt-2 text-neutral-400">
            <span>
              High: <strong className="text-orange-400">{highIncidents.length}</strong> • Med:{' '}
              <strong className="text-yellow-400">{mediumIncidents.length}</strong>
            </span>
            <span className="text-emerald-400 font-medium">{resolvedIncidents.length} Resolved</span>
          </div>
        </div>

        {/* Card 3: Kubernetes Workloads */}
        <div className="bg-neutral-900 border border-neutral-800 p-3.5 rounded shadow-lg">
          <div className="flex items-center justify-between text-[11px] text-neutral-400 font-semibold mb-1">
            <span>KUBERNETES RESOURCES</span>
            <Cpu className="w-4 h-4 text-purple-400" />
          </div>
          <div className="flex items-baseline gap-3 mb-2">
            <div>
              <span className="text-2xl font-bold text-neutral-100">{totalPods}</span>
              <span className="text-neutral-500 text-[10px] ml-1">Pods</span>
            </div>
            <div className="border-l border-neutral-800 pl-3">
              <span className="text-xl font-bold text-neutral-300">{totalNodes}</span>
              <span className="text-neutral-500 text-[10px] ml-1">Nodes</span>
            </div>
          </div>
          <div className="text-[11px] text-neutral-400 border-t border-neutral-800/80 pt-2">
            Active in <strong className="text-neutral-200">{totalNamespaces}</strong> Namespaces
          </div>
        </div>

        {/* Card 4: Agents Health */}
        <div className="bg-neutral-900 border border-neutral-800 p-3.5 rounded shadow-lg">
          <div className="flex items-center justify-between text-[11px] text-neutral-400 font-semibold mb-1">
            <span>SKYOPS AGENTS</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 mb-2">
            {healthyAgents} / {totalClusters} <span className="text-xs text-neutral-400 font-normal">Healthy</span>
          </div>
          <div className="text-[11px] text-neutral-400 border-t border-neutral-800/80 pt-2 flex justify-between">
            <span>Telemetry Outbox Sync:</span>
            <span className="text-emerald-400 font-semibold">5s Polling</span>
          </div>
        </div>
      </div>

      {/* Main Content 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left Column (2-Span): Recent Incidents List */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between bg-neutral-900 border border-neutral-800 p-3 rounded">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span className="font-bold text-neutral-100 text-sm">RECENT ACTIVE INCIDENTS</span>
            </div>
            <button
              onClick={() => onNavigateTab('incidents')}
              className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300 font-semibold text-xs"
            >
              <span>VIEW ALL ({incidents.length})</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="border border-neutral-800 rounded bg-neutral-950 overflow-hidden shadow-xl">
            {recentIncidents.length === 0 ? (
              <div className="p-8 text-center text-neutral-500 font-mono">
                No active incidents recorded. Cluster is operating within normal bounds.
              </div>
            ) : (
              <div className="divide-y divide-neutral-800">
                {recentIncidents.map((inc) => (
                  <div
                    key={inc.incident_id}
                    onClick={() => onSelectIncident(inc)}
                    className="p-3 hover:bg-neutral-900/80 cursor-pointer transition-colors flex items-center justify-between gap-3 group"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <SeverityBadge severity={inc.severity} />
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-cyan-400 group-hover:underline">
                            {inc.incident_id}
                          </span>
                          <span className="font-bold text-neutral-200 truncate">
                            {inc.resource?.name}
                          </span>
                          <span className="text-[10px] text-neutral-400">
                            (ns/{inc.resource?.namespace || 'default'})
                          </span>
                        </div>
                        <div className="text-[11px] text-neutral-400 truncate mt-0.5">
                          {inc.current_state}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <StatusBadge status={inc.status} />
                      <div className="text-right text-[11px] text-neutral-400">
                        <div>{formatRelativeTime(inc.last_seen)}</div>
                        <div className="text-[10px] text-neutral-500">
                          {inc.cluster_id.replace('skyops-cluster-', '')}
                        </div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-neutral-600 group-hover:text-cyan-400 transition-colors" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Cluster Health & Operational Telemetry */}
        <div className="space-y-4">
          {/* Cluster Status Box */}
          <div className="bg-neutral-900 border border-neutral-800 rounded p-3.5 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-neutral-800">
              <span className="font-bold text-neutral-100 text-sm flex items-center gap-1.5">
                <Server className="w-4 h-4 text-cyan-400" />
                CLUSTER HEALTH
              </span>
              <button
                onClick={() => onNavigateTab('clusters')}
                className="text-cyan-400 hover:text-cyan-300 text-xs font-semibold"
              >
                MANAGE
              </button>
            </div>

            <div className="space-y-2">
              {clusters.map((c) => {
                const openCount = incidents.filter(
                  (i) => i.cluster_id === c.cluster_id && i.status === 'OPEN'
                ).length;
                return (
                  <div
                    key={c.cluster_id}
                    onClick={() => onSelectCluster(c.cluster_id)}
                    className="p-2.5 bg-neutral-950 border border-neutral-800 rounded hover:border-neutral-700 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-neutral-200">{c.name}</span>
                      <span className="px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px]">
                        {c.status}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-neutral-400">
                      <span>
                        {c.node_count} Nodes • {c.pod_count} Pods
                      </span>
                      {openCount > 0 ? (
                        <span className="text-amber-400 font-bold">{openCount} Incidents</span>
                      ) : (
                        <span className="text-emerald-400">0 Incidents</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Activity Stream Preview */}
          <div className="bg-neutral-900 border border-neutral-800 rounded p-3.5 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-neutral-800">
              <span className="font-bold text-neutral-100 text-sm flex items-center gap-1.5">
                <Radio className="w-4 h-4 text-emerald-400" />
                EVENT STREAM
              </span>
              <button
                onClick={() => onNavigateTab('events')}
                className="text-cyan-400 hover:text-cyan-300 text-xs font-semibold"
              >
                STREAM
              </button>
            </div>

            <div className="space-y-2 text-[11px] font-mono">
              <div className="p-2 bg-neutral-950 border border-neutral-800/80 rounded">
                <div className="flex items-center justify-between text-neutral-500 text-[10px] mb-0.5">
                  <span className="text-amber-400 font-bold">[K8s.Watcher]</span>
                  <span>Just now</span>
                </div>
                <div className="text-neutral-300">Pod event stream monitored continuously</div>
              </div>

              <div className="p-2 bg-neutral-950 border border-neutral-800/80 rounded">
                <div className="flex items-center justify-between text-neutral-500 text-[10px] mb-0.5">
                  <span className="text-emerald-400 font-bold">[Cloud.SyncWorker]</span>
                  <span>5s ago</span>
                </div>
                <div className="text-neutral-300">Outbox queue synced with SkyOps Cloud API</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
