import React, { useEffect, useState } from 'react';
import {
  Activity,
  CheckCircle2,
  Cpu,
  Database,
  HardDrive,
  Layers,
  Radio,
  Server,
  ShieldAlert,
  AlertTriangle,
} from 'lucide-react';
import { ClusterInfo, K8sNode, NavTabType, NodeMetric } from '../types';
import { apiService } from '../services/api';

interface ClusterOverviewProps {
  clusters: ClusterInfo[];
  selectedClusterId: string;
  onSelectCluster: (clusterId: string) => void;
  onNavigateTab?: (tab: NavTabType) => void;
}

export const ClusterOverview: React.FC<ClusterOverviewProps> = ({
  clusters,
  selectedClusterId,
  onSelectCluster,
  onNavigateTab,
}) => {
  const [nodes, setNodes] = useState<NodeMetric[]>([]);
  const [loadingNodes, setLoadingNodes] = useState<boolean>(true);

  const currentCluster =
    clusters.find((c) => c.cluster_id === selectedClusterId) || clusters[0];

  useEffect(() => {
    let isMounted = true;
    setLoadingNodes(true);
    apiService
      .fetchNodeMetrics(selectedClusterId)
      .then((data) => {
        if (isMounted) {
          setNodes(data || []);
          setLoadingNodes(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setNodes([]);
          setLoadingNodes(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, [selectedClusterId]);

  if (!clusters || clusters.length === 0) {
    return (
      <div className="bg-neutral-900 border border-neutral-800 rounded p-8 text-center text-neutral-400 font-mono text-xs">
        <Server className="w-8 h-8 text-neutral-600 mx-auto mb-2" />
        <p className="font-bold text-neutral-200 text-sm">No Clusters Registered</p>
        <p className="text-neutral-500 mt-1">Deploy the SkyOps Agent to register your Kubernetes clusters.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 font-mono text-xs text-neutral-200">
      {/* Multi-Cluster Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {clusters.map((c) => {
          const isSelected = selectedClusterId === c.cluster_id;
          return (
            <div
              key={c.cluster_id}
              onClick={() => onSelectCluster(c.cluster_id)}
              className={`p-3 rounded border cursor-pointer transition-all ${
                isSelected
                  ? 'bg-neutral-900 border-cyan-500 shadow-xl'
                  : 'bg-neutral-950 border-neutral-800 hover:border-neutral-700 hover:bg-neutral-900/60'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="font-bold text-neutral-100 flex items-center gap-1.5 text-sm">
                  <Server className="w-4 h-4 text-cyan-400" />
                  <span>{c.name}</span>
                </div>
                <span className="px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px]">
                  {c.status}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2 py-2 border-y border-neutral-800/80 text-[11px] my-2">
                <div>
                  <div className="text-[10px] text-neutral-500">VERSION</div>
                  <div className="font-semibold text-neutral-300 truncate">{c.kubernetes_version}</div>
                </div>
                <div>
                  <div className="text-[10px] text-neutral-500">NODES</div>
                  <div className="font-bold text-neutral-200">{c.node_count}</div>
                </div>
                <div>
                  <div className="text-[10px] text-neutral-500">PODS</div>
                  <div className="font-bold text-neutral-200">{c.pod_count}</div>
                </div>
              </div>

              <div className="flex items-center justify-between text-[10px] text-neutral-500 pt-1">
                <span>Agent: {c.agent_status || 'HEALTHY'}</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectCluster(c.cluster_id);
                    if (onNavigateTab) onNavigateTab('incidents');
                  }}
                  className="px-2 py-0.5 bg-cyan-950 text-cyan-400 hover:bg-cyan-900 border border-cyan-800 rounded font-bold transition-colors cursor-pointer"
                >
                  VIEW INCIDENTS
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Cluster Nodes & Hardware Resources */}
      {currentCluster && (
        <div className="bg-neutral-900 border border-neutral-800 rounded p-4">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-neutral-800">
            <div className="font-bold text-neutral-100 text-sm flex items-center gap-2">
              <Cpu className="w-4 h-4 text-cyan-400" />
              <span>KUBERNETES NODES IN {currentCluster.name.toUpperCase()}</span>
            </div>
            <span className="text-[10px] text-neutral-400">
              Configured Nodes: {currentCluster.node_count}
            </span>
          </div>

          {loadingNodes ? (
            <div className="py-6 text-center text-neutral-500">Loading node metrics...</div>
          ) : nodes.length === 0 ? (
            <div className="py-6 text-center text-neutral-500 space-y-1">
              <p className="font-bold text-neutral-400">No node metrics reported for this cluster</p>
              <p className="text-[11px]">Requires Kubernetes metrics-server and SkyOps Agent connection.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-xs">
                <thead>
                  <tr className="border-b border-neutral-800 bg-neutral-950 text-neutral-500 uppercase text-[10px]">
                    <th className="py-2 px-3">NODE NAME</th>
                    <th className="py-2 px-3">STATUS</th>
                    <th className="py-2 px-3 w-40">CPU UTILIZATION</th>
                    <th className="py-2 px-3 w-40">MEMORY UTILIZATION</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800">
                  {nodes.map((node, idx) => {
                    const isNotReady = node.status !== 'Ready';
                    return (
                      <tr key={idx} className="hover:bg-neutral-950/60">
                        <td className="py-2.5 px-3 font-bold text-neutral-200">{node.name}</td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
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
                            <div className="w-full h-1.5 bg-neutral-950 rounded overflow-hidden">
                              <div
                                className={`h-full ${
                                  (node.cpu_pct || 0) > 80 ? 'bg-red-500' : (node.cpu_pct || 0) > 60 ? 'bg-amber-500' : 'bg-cyan-500'
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
                            <div className="w-full h-1.5 bg-neutral-950 rounded overflow-hidden">
                              <div
                                className={`h-full ${
                                  (node.memory_pct || 0) > 85 ? 'bg-red-500' : (node.memory_pct || 0) > 70 ? 'bg-amber-500' : 'bg-emerald-500'
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
            </div>
          )}
        </div>
      )}
    </div>
  );
};
