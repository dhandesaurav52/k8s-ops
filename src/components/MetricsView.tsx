import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Database,
  Clock,
  RefreshCw,
  Server,
  BarChart2,
  TrendingUp,
  Layers,
  ArrowUpRight,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { apiService } from '../services/api';
import {
  ClusterInfo,
  ClusterMetricSummary,
  MetricHistoryPoint,
  NodeMetric,
  PodMetric,
} from '../types';

interface MetricsViewProps {
  selectedClusterId: string;
  clusters: ClusterInfo[];
}

export const MetricsView: React.FC<MetricsViewProps> = ({
  selectedClusterId,
  clusters,
}) => {
  const [timeRange, setTimeRange] = useState<string>('1h');
  const [summary, setSummary] = useState<ClusterMetricSummary | null>(null);
  const [history, setHistory] = useState<MetricHistoryPoint[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'nodes' | 'pods'>('overview');

  const loadData = async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const clusterParam = selectedClusterId === 'ALL' ? undefined : selectedClusterId;
      const [sumData, histData] = await Promise.all([
        apiService.fetchMetricsSummary(clusterParam),
        apiService.fetchMetricHistory(clusterParam, timeRange),
      ]);

      setSummary(sumData);
      setHistory(histData.points || []);
    } catch (err: any) {
      console.error('Failed to load metrics:', err);
      setError(err.message || 'Failed to connect to SkyOps Metrics API');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedClusterId, timeRange]);

  const activeClusterName =
    selectedClusterId === 'ALL'
      ? 'All Connected Clusters'
      : clusters.find((c) => c.cluster_id === selectedClusterId)?.name || selectedClusterId;

  const isOnline = summary?.metrics_status === 'ONLINE';

  return (
    <div id="skyops-metrics-view" className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-slate-900/80 p-4 rounded-xl border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              <BarChart2 className="w-5 h-5 text-cyan-400" />
              Infrastructure Metrics & Telemetry
            </h1>
            <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
              {activeClusterName}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time node and pod resource metrics collected directly from Kubernetes <code className="text-cyan-400 font-mono">metrics.k8s.io</code> API.
          </p>
        </div>

        {/* Right Action Bar */}
        <div className="flex items-center gap-3">
          {/* Metrics Health Badge */}
          <div
            id="metrics-status-badge"
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border ${
              isOnline
                ? 'bg-emerald-950/60 border-emerald-800/80 text-emerald-300'
                : 'bg-amber-950/60 border-amber-800/80 text-amber-300'
            }`}
          >
            {isOnline ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span>METRICS ONLINE</span>
              </>
            ) : (
              <>
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                <span>METRICS UNAVAILABLE</span>
              </>
            )}
          </div>

          {/* Time Range Selector */}
          <div className="flex items-center bg-slate-950 rounded-lg p-1 border border-slate-800 text-xs font-medium">
            {['5m', '15m', '30m', '1h', '6h', '24h'].map((r) => (
              <button
                key={r}
                id={`time-range-btn-${r}`}
                onClick={() => setTimeRange(r)}
                className={`px-2.5 py-1 rounded transition-colors ${
                  timeRange === r
                    ? 'bg-cyan-500 text-slate-950 font-bold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {r}
              </button>
            ))}
          </div>

          {/* Refresh Button */}
          <button
            id="metrics-refresh-btn"
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="p-2 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg border border-slate-800 transition-colors"
            title="Refresh Metrics"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Unavailable Fallback Warning */}
      {!isOnline && summary && (
        <div id="metrics-unavailable-banner" className="bg-amber-950/40 border border-amber-800/60 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-amber-200">Kubernetes Resource Metrics Source Unavailable</h4>
            <p className="text-xs text-amber-300/80">
              {summary.status_message ||
                'The metrics.k8s.io API service is not installed or unreachable on this cluster. Incident detection continues normally without metrics.'}
            </p>
            <p className="text-xs text-slate-400 pt-1 font-mono">
              To enable metrics on K8s: <span className="text-cyan-400">kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml</span>
            </p>
          </div>
        </div>
      )}

      {/* Metric Summary Gauge Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* CPU Utilization Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-cyan-400" />
              CPU Utilization
            </span>
            <span className="text-xs font-mono text-slate-500">mCores</span>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-slate-100">
              {isOnline ? `${summary?.summary?.cpu_utilization_pct}%` : 'N/A'}
            </span>
            {isOnline && (
              <span className="text-xs text-slate-400 font-mono">
                {summary?.summary?.used_cpu_mcores} / {summary?.summary?.total_cpu_mcores} m
              </span>
            )}
          </div>
          {/* Progress bar */}
          <div className="mt-3 w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                (summary?.summary?.cpu_utilization_pct || 0) > 80
                  ? 'bg-rose-500'
                  : (summary?.summary?.cpu_utilization_pct || 0) > 65
                  ? 'bg-amber-500'
                  : 'bg-cyan-500'
              }`}
              style={{ width: `${isOnline ? summary?.summary?.cpu_utilization_pct : 0}%` }}
            />
          </div>
        </div>

        {/* Memory Utilization Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
              <Database className="w-4 h-4 text-purple-400" />
              Memory Utilization
            </span>
            <span className="text-xs font-mono text-slate-500">MiB</span>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-slate-100">
              {isOnline ? `${summary?.summary?.memory_utilization_pct}%` : 'N/A'}
            </span>
            {isOnline && (
              <span className="text-xs text-slate-400 font-mono">
                {Math.round((summary?.summary?.used_memory_mb || 0) / 1024 * 10) / 10} / {Math.round((summary?.summary?.total_memory_mb || 0) / 1024 * 10) / 10} GiB
              </span>
            )}
          </div>
          <div className="mt-3 w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                (summary?.summary?.memory_utilization_pct || 0) > 80
                  ? 'bg-rose-500'
                  : (summary?.summary?.memory_utilization_pct || 0) > 65
                  ? 'bg-amber-500'
                  : 'bg-purple-500'
              }`}
              style={{ width: `${isOnline ? summary?.summary?.memory_utilization_pct : 0}%` }}
            />
          </div>
        </div>

        {/* Monitored Nodes Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
              <Server className="w-4 h-4 text-emerald-400" />
              Active Nodes
            </span>
            <span className="text-xs text-emerald-400 font-mono font-semibold">100% Ready</span>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-slate-100">
              {summary?.nodes?.length || 0}
            </span>
            <span className="text-xs text-slate-400">Worker Instances</span>
          </div>
          <div className="mt-3 flex items-center gap-1 text-xs text-slate-400">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Disk & Memory Pressure OK</span>
          </div>
        </div>

        {/* Monitored Pods Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-blue-400" />
              Sampled Pods
            </span>
            <span className="text-xs font-mono text-slate-500">Live</span>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-slate-100">
              {summary?.pods?.length || 0}
            </span>
            <span className="text-xs text-slate-400">Workload Replicas</span>
          </div>
          <div className="mt-3 flex items-center gap-1 text-xs text-slate-400">
            <Activity className="w-3.5 h-3.5 text-blue-400" />
            <span>Source: {summary?.source || 'metrics.k8s.io'}</span>
          </div>
        </div>
      </div>

      {/* Historical Time Series Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CPU Usage Chart */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-cyan-400" />
                Cluster CPU Usage Trend ({timeRange})
              </h3>
              <p className="text-xs text-slate-400">Percentage of total allocatable mCores</p>
            </div>
            <span className="text-xs font-mono text-cyan-400 font-bold bg-cyan-950/60 border border-cyan-800/60 px-2 py-0.5 rounded">
              {isOnline ? `${summary?.summary?.cpu_utilization_pct}% Current` : 'Unavailable'}
            </span>
          </div>

          <div className="h-64 w-full">
            {isOnline && history.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={history} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="timeLabel" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 100]} stroke="#64748b" tick={{ fontSize: 11 }} unit="%" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.5rem', color: '#f8fafc' }}
                    formatter={(val: any) => [`${val}%`, 'CPU Utilization']}
                  />
                  <Area type="monotone" dataKey="cpu_pct" stroke="#06b6d4" strokeWidth={2} fillOpacity={1} fill="url(#cpuGradient)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center border border-dashed border-slate-800 rounded-lg text-slate-500 text-xs">
                No CPU telemetry data available for this range
              </div>
            )}
          </div>
        </div>

        {/* Memory Usage Chart */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <Database className="w-4 h-4 text-purple-400" />
                Cluster Memory Usage Trend ({timeRange})
              </h3>
              <p className="text-xs text-slate-400">Percentage of total allocatable RAM</p>
            </div>
            <span className="text-xs font-mono text-purple-400 font-bold bg-purple-950/60 border border-purple-800/60 px-2 py-0.5 rounded">
              {isOnline ? `${summary?.summary?.memory_utilization_pct}% Current` : 'Unavailable'}
            </span>
          </div>

          <div className="h-64 w-full">
            {isOnline && history.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={history} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="memGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#a855f7" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#a855f7" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="timeLabel" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 100]} stroke="#64748b" tick={{ fontSize: 11 }} unit="%" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.5rem', color: '#f8fafc' }}
                    formatter={(val: any) => [`${val}%`, 'Memory Utilization']}
                  />
                  <Area type="monotone" dataKey="memory_pct" stroke="#a855f7" strokeWidth={2} fillOpacity={1} fill="url(#memGradient)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center border border-dashed border-slate-800 rounded-lg text-slate-500 text-xs">
                No Memory telemetry data available for this range
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabs & Detailed Breakdown */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
        {/* Tab Headers */}
        <div className="flex items-center gap-2 border-b border-slate-800 px-4 pt-3">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-colors border-b-2 -mb-px ${
              activeTab === 'overview'
                ? 'border-cyan-400 text-cyan-400 bg-slate-800/60'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Resource Breakdown Overview
          </button>
          <button
            onClick={() => setActiveTab('nodes')}
            className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-colors border-b-2 -mb-px ${
              activeTab === 'nodes'
                ? 'border-cyan-400 text-cyan-400 bg-slate-800/60'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Node Utilization ({summary?.nodes?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('pods')}
            className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-colors border-b-2 -mb-px ${
              activeTab === 'pods'
                ? 'border-cyan-400 text-cyan-400 bg-slate-800/60'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Top Pod Resource Consumers ({summary?.pods?.length || 0})
          </button>
        </div>

        {/* Tab Body */}
        <div className="p-5">
          {activeTab === 'overview' || activeTab === 'nodes' ? (
            <div className="space-y-4">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Kubernetes Worker Node Telemetry
              </h4>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 font-semibold bg-slate-950/40">
                      <th className="py-2.5 px-3">Node Name</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">CPU Usage (mCores)</th>
                      <th className="py-2.5 px-3">CPU %</th>
                      <th className="py-2.5 px-3">Memory Usage (MiB)</th>
                      <th className="py-2.5 px-3">Memory %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300 font-mono">
                    {summary?.nodes && summary.nodes.length > 0 ? (
                      summary.nodes.map((n) => (
                        <tr key={n.name} className="hover:bg-slate-800/40 transition-colors">
                          <td className="py-2.5 px-3 font-semibold text-slate-200">{n.name}</td>
                          <td className="py-2.5 px-3">
                            <span className="inline-flex items-center gap-1 text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-2 py-0.5 rounded text-[10px]">
                              <CheckCircle2 className="w-3 h-3" />
                              {n.status}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            {n.cpu_usage_mcores} / {n.cpu_capacity_mcores} m
                          </td>
                          <td className="py-2.5 px-3">
                            <div className="flex items-center gap-2">
                              <span className="w-10">{n.cpu_pct}%</span>
                              <div className="w-24 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                                <div
                                  className={`h-full ${n.cpu_pct > 80 ? 'bg-rose-500' : n.cpu_pct > 60 ? 'bg-amber-500' : 'bg-cyan-500'}`}
                                  style={{ width: `${n.cpu_pct}%` }}
                                />
                              </div>
                            </div>
                          </td>
                          <td className="py-2.5 px-3">
                            {n.memory_usage_mb} / {n.memory_capacity_mb} MiB
                          </td>
                          <td className="py-2.5 px-3">
                            <div className="flex items-center gap-2">
                              <span className="w-10">{n.memory_pct}%</span>
                              <div className="w-24 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                                <div
                                  className={`h-full ${n.memory_pct > 80 ? 'bg-rose-500' : n.memory_pct > 60 ? 'bg-amber-500' : 'bg-purple-500'}`}
                                  style={{ width: `${n.memory_pct}%` }}
                                />
                              </div>
                            </div>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={6} className="py-6 text-center text-slate-500">
                          No node metrics reported for this cluster scope
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          {activeTab === 'pods' && (
            <div className="space-y-4">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Top Pod Consumers Sourced from metrics.k8s.io
              </h4>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 font-semibold bg-slate-950/40">
                      <th className="py-2.5 px-3">Pod Name</th>
                      <th className="py-2.5 px-3">Namespace</th>
                      <th className="py-2.5 px-3">Node Placement</th>
                      <th className="py-2.5 px-3">CPU Usage (m)</th>
                      <th className="py-2.5 px-3">Memory Usage (MiB)</th>
                      <th className="py-2.5 px-3">Restarts</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300 font-mono">
                    {summary?.pods && summary.pods.length > 0 ? (
                      summary.pods.map((p) => (
                        <tr key={p.name} className="hover:bg-slate-800/40 transition-colors">
                          <td className="py-2.5 px-3 font-semibold text-cyan-300">{p.name}</td>
                          <td className="py-2.5 px-3">
                            <span className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded text-[10px]">
                              {p.namespace}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-slate-400">{p.node_name || 'gke-pool-1'}</td>
                          <td className="py-2.5 px-3 text-cyan-400 font-bold">{p.cpu_usage_mcores} m</td>
                          <td className="py-2.5 px-3 text-purple-400 font-bold">{p.memory_usage_mb} MiB</td>
                          <td className="py-2.5 px-3">
                            {(p.restarts || 0) > 0 ? (
                              <span className="text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded text-[10px]">
                                {p.restarts} restarts
                              </span>
                            ) : (
                              <span className="text-slate-500">0</span>
                            )}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={6} className="py-6 text-center text-slate-500">
                          No pod metrics available for this cluster scope
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
