import React, { useEffect, useState } from 'react';
import { Cpu, Search, Server, CheckCircle2, Filter, AlertCircle } from 'lucide-react';
import { ClusterInfo, NodeMetric } from '../types';
import { apiService } from '../services/api';

interface NodesViewProps {
  clusters: ClusterInfo[];
  selectedClusterId: string;
  onSelectCluster: (clusterId: string) => void;
}

export const NodesView: React.FC<NodesViewProps> = ({
  clusters,
  selectedClusterId,
  onSelectCluster,
}) => {
  const [nodes, setNodes] = useState<NodeMetric[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'Ready' | 'NotReady'>('ALL');

  const selectedCluster = clusters.find((c) => c.cluster_id === selectedClusterId);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    apiService
      .fetchNodeMetrics(selectedClusterId)
      .then((data) => {
        if (isMounted) {
          setNodes(data || []);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setNodes([]);
          setLoading(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, [selectedClusterId]);

  const filteredNodes = nodes.filter((node) => {
    if (statusFilter !== 'ALL' && node.status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        node.name.toLowerCase().includes(q) ||
        (node.cluster_id && node.cluster_id.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const readyNodeCount = nodes.filter((n) => n.status === 'Ready').length;

  return (
    <div className="space-y-4 font-mono text-xs text-neutral-200">
      {/* Backend Telemetry Notice */}
      <div className="bg-neutral-900 border border-neutral-800 p-2.5 rounded flex items-center justify-between text-[11px]">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-cyan-400 shrink-0" />
          <span>
            <strong className="text-cyan-300">Node Telemetry:</strong> Real node telemetry sourced from Kubernetes <code className="text-cyan-400 font-mono">metrics.k8s.io</code> stream via SkyOps Agent.
          </span>
        </div>
        {selectedCluster && (
          <span className="px-2 py-0.5 rounded bg-neutral-950 border border-neutral-800 font-bold text-neutral-300">
            Scope: {selectedCluster.name}
          </span>
        )}
      </div>

      {/* Node Capacity Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 bg-neutral-900 border border-neutral-800 p-3.5 rounded shadow-lg">
        <div>
          <div className="text-[10px] text-neutral-500 uppercase">ACTIVE NODES</div>
          <div className="text-xl font-bold text-neutral-100 flex items-center gap-1.5 mt-0.5">
            <Cpu className="w-4 h-4 text-cyan-400" />
            {nodes.length} Nodes
          </div>
        </div>

        <div>
          <div className="text-[10px] text-neutral-500 uppercase">NODE READINESS</div>
          <div className="text-xl font-bold text-emerald-400 flex items-center gap-1.5 mt-0.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            {readyNodeCount} / {nodes.length} Ready
          </div>
        </div>

        <div>
          <div className="text-[10px] text-neutral-500 uppercase">CLUSTER SCOPE</div>
          <div className="text-xl font-bold text-cyan-400 mt-0.5 truncate">
            {selectedCluster ? selectedCluster.name : selectedClusterId || 'ALL'}
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-neutral-900 border border-neutral-800 p-2.5 rounded">
        <div className="flex items-center gap-3">
          <div className="relative w-64">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search nodes by name..."
              className="w-full bg-neutral-950 border border-neutral-800 rounded pl-8 pr-3 py-1 text-xs text-neutral-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-neutral-500" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-xs text-neutral-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="ALL">Status: ALL</option>
              <option value="Ready">Status: Ready</option>
              <option value="NotReady">Status: NotReady</option>
            </select>
          </div>
        </div>

        <div className="text-neutral-400 text-[11px]">
          Showing <strong className="text-neutral-200">{filteredNodes.length}</strong> nodes
        </div>
      </div>

      {/* Nodes Table */}
      <div className="border border-neutral-800 rounded bg-neutral-950 overflow-x-auto shadow-xl">
        {loading ? (
          <div className="py-8 text-center text-neutral-500 font-mono">Loading node telemetry...</div>
        ) : filteredNodes.length === 0 ? (
          <div className="py-8 text-center text-neutral-500 font-mono space-y-1">
            <p className="font-bold text-neutral-400">No nodes found for cluster scope</p>
            <p className="text-[11px]">Requires active SkyOps Agent reporting node metrics.</p>
          </div>
        ) : (
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-neutral-800 bg-neutral-900/90 text-neutral-400 uppercase text-[10px] tracking-wider">
                <th className="py-2.5 px-3 font-semibold">NODE NAME</th>
                <th className="py-2.5 px-3 font-semibold">CLUSTER</th>
                <th className="py-2.5 px-3 font-semibold">STATUS</th>
                <th className="py-2.5 px-3 font-semibold w-44">CPU UTILIZATION</th>
                <th className="py-2.5 px-3 font-semibold w-44">MEMORY UTILIZATION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800/80">
              {filteredNodes.map((node, idx) => {
                const isNotReady = node.status !== 'Ready';
                return (
                  <tr key={idx} className="hover:bg-neutral-900/80 transition-colors">
                    <td className="py-2.5 px-3 font-bold text-neutral-100 flex items-center gap-1.5">
                      <Server className="w-3.5 h-3.5 text-neutral-500" />
                      <span>{node.name}</span>
                    </td>
                    <td className="py-2.5 px-3 text-neutral-400">{node.cluster_id || 'prod'}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          isNotReady
                            ? 'bg-red-950 text-red-400 border border-red-800'
                            : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        }`}
                      >
                        {node.status || 'Ready'}
                      </span>
                    </td>

                    <td className="py-2.5 px-3">
                      <div className="space-y-1">
                        <div className="flex justify-between text-[10px]">
                          <span>{node.cpu_pct || 0}%</span>
                          <span className="text-neutral-500">{node.cpu_usage_mcores || 0} mCores</span>
                        </div>
                        <div className="w-full h-1.5 bg-neutral-900 rounded overflow-hidden">
                          <div
                            className={`h-full ${
                              (node.cpu_pct || 0) > 80
                                ? 'bg-red-500'
                                : (node.cpu_pct || 0) > 60
                                ? 'bg-amber-500'
                                : 'bg-cyan-500'
                            }`}
                            style={{ width: `${Math.min(node.cpu_pct || 0, 100)}%` }}
                          />
                        </div>
                      </div>
                    </td>

                    <td className="py-2.5 px-3">
                      <div className="space-y-1">
                        <div className="flex justify-between text-[10px]">
                          <span>{node.memory_pct || 0}%</span>
                          <span className="text-neutral-500">{node.memory_usage_mb || 0} MB</span>
                        </div>
                        <div className="w-full h-1.5 bg-neutral-900 rounded overflow-hidden">
                          <div
                            className={`h-full ${
                              (node.memory_pct || 0) > 85
                                ? 'bg-red-500'
                                : (node.memory_pct || 0) > 70
                                ? 'bg-amber-500'
                                : 'bg-emerald-500'
                            }`}
                            style={{ width: `${Math.min(node.memory_pct || 0, 100)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
