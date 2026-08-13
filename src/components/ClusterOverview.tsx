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
  Plus,
  Copy,
  Check,
  X,
  Terminal,
} from 'lucide-react';
import { ClusterInfo, K8sNode, NavTabType, NodeMetric } from '../types';
import { apiService } from '../services/api';

interface ClusterOverviewProps {
  clusters: ClusterInfo[];
  selectedClusterId: string;
  onSelectCluster: (clusterId: string) => void;
  onNavigateTab?: (tab: NavTabType) => void;
  onClusterAdded?: () => void;
}

export const ClusterOverview: React.FC<ClusterOverviewProps> = ({
  clusters,
  selectedClusterId,
  onSelectCluster,
  onNavigateTab,
  onClusterAdded,
}) => {
  const [nodes, setNodes] = useState<NodeMetric[]>([]);
  const [loadingNodes, setLoadingNodes] = useState<boolean>(true);
  const [showOnboardModal, setShowOnboardModal] = useState<boolean>(false);
  const [clusterNameInput, setClusterNameInput] = useState<string>('');
  const [onboardLoading, setOnboardLoading] = useState<boolean>(false);
  const [onboardError, setOnboardError] = useState<string | null>(null);
  const [onboardData, setOnboardData] = useState<{ cluster_id: string; helm_command: string } | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

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

  const handleOnboardCluster = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clusterNameInput.trim()) return;
    setOnboardLoading(true);
    setOnboardError(null);
    try {
      const res = await apiService.onboardCluster(clusterNameInput.trim());
      setOnboardData(res);
      if (onClusterAdded) onClusterAdded();
    } catch (err: any) {
      setOnboardError(err.message || 'Failed to generate onboarding command');
    } finally {
      setOnboardLoading(false);
    }
  };

  const copyHelmCommand = () => {
    if (!onboardData?.helm_command) return;
    navigator.clipboard.writeText(onboardData.helm_command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4 font-mono text-xs text-neutral-200">
      {/* Header bar with Add Cluster Button */}
      <div className="flex items-center justify-between bg-neutral-900 border border-neutral-800 rounded p-3">
        <div>
          <h2 className="font-bold text-sm text-neutral-100 flex items-center gap-2">
            <Server className="w-4 h-4 text-cyan-400" />
            <span>KUBERNETES CLUSTERS ({clusters.length})</span>
          </h2>
          <p className="text-[11px] text-neutral-400">Install the SkyOps Agent in your Kubernetes cluster to begin incident management.</p>
        </div>
        <button
          type="button"
          onClick={() => {
            setOnboardData(null);
            setOnboardError(null);
            setClusterNameInput('');
            setShowOnboardModal(true);
          }}
          className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-neutral-950 font-bold rounded flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>CONNECT NEW CLUSTER</span>
        </button>
      </div>

      {clusters.length === 0 ? (
        <div className="bg-neutral-900 border border-neutral-800 rounded p-8 text-center text-neutral-400 font-mono text-xs">
          <Server className="w-8 h-8 text-neutral-600 mx-auto mb-2" />
          <p className="font-bold text-neutral-200 text-sm">No Clusters Registered</p>
          <p className="text-neutral-500 mt-1 mb-4">Click "Connect New Cluster" to generate your Helm agent installation command.</p>
          <button
            type="button"
            onClick={() => setShowOnboardModal(true)}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-neutral-950 font-bold rounded inline-flex items-center gap-2 transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>CONNECT NEW CLUSTER</span>
          </button>
        </div>
      ) : (
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
                  <span className={`px-1.5 py-0.2 rounded text-[10px] border ${
                    c.status === 'CONNECTED' 
                      ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                      : 'bg-neutral-900 text-neutral-400 border-neutral-800'
                  }`}>
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
      )}

      {/* Modal for Onboarding Cluster */}
      {showOnboardModal && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-lg max-w-xl w-full p-6 space-y-4 relative">
            <button
              onClick={() => setShowOnboardModal(false)}
              className="absolute top-4 right-4 text-neutral-400 hover:text-neutral-100"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2 border-b border-neutral-800 pb-3">
              <Server className="w-5 h-5 text-cyan-400" />
              <h3 className="text-base font-bold text-neutral-100">Connect Kubernetes Cluster</h3>
            </div>

            {!onboardData ? (
              <form onSubmit={handleOnboardCluster} className="space-y-4">
                <p className="text-neutral-300 text-xs leading-relaxed">
                  Enter a name for your Kubernetes cluster (e.g. <span className="text-cyan-400">production-eks</span>, <span className="text-cyan-400">staging-gke</span>).
                  We will generate a unique agent token and Helm installation command for your cluster.
                </p>

                {onboardError && (
                  <div className="bg-red-950/80 border border-red-800 text-red-200 p-3 rounded text-xs">
                    {onboardError}
                  </div>
                )}

                <div>
                  <label className="block text-[11px] text-neutral-400 uppercase font-bold mb-1">
                    Cluster Name
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. production-us-east"
                    value={clusterNameInput}
                    onChange={(e) => setClusterNameInput(e.target.value)}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded px-3 py-2 text-neutral-100 focus:outline-none focus:border-cyan-500 font-mono text-xs"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowOnboardModal(false)}
                    className="px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded font-bold transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={onboardLoading || !clusterNameInput.trim()}
                    className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-neutral-950 font-bold rounded transition-colors cursor-pointer"
                  >
                    {onboardLoading ? 'Generating Token...' : 'Generate Helm Command'}
                  </button>
                </div>
              </form>
            ) : (
              <div className="space-y-4">
                <div className="bg-emerald-950/60 border border-emerald-800 text-emerald-200 p-3 rounded text-xs">
                  Cluster <span className="font-bold text-white">{onboardData.cluster_id}</span> created! Run the Helm command below in your cluster terminal:
                </div>

                <div className="relative bg-neutral-950 border border-neutral-800 rounded p-4 font-mono text-[11px]">
                  <div className="flex items-center justify-between text-neutral-500 text-[10px] mb-2 border-b border-neutral-800/80 pb-1">
                    <span className="flex items-center gap-1.5"><Terminal className="w-3.5 h-3.5 text-cyan-400" /> HELM AGENT INSTALLATION</span>
                    <button
                      onClick={copyHelmCommand}
                      className="text-cyan-400 hover:text-cyan-300 font-bold flex items-center gap-1 cursor-pointer"
                    >
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copied ? 'COPIED!' : 'COPY'}</span>
                    </button>
                  </div>
                  <pre className="text-neutral-200 whitespace-pre-wrap overflow-x-auto leading-relaxed">
                    {onboardData.helm_command}
                  </pre>
                </div>

                <p className="text-[11px] text-neutral-400 leading-relaxed">
                  Once the agent pod starts, it will automatically establish outbound telemetry and your cluster will appear as <span className="text-emerald-400 font-bold">CONNECTED</span> in SkyOps.
                </p>

                <div className="flex justify-end pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setShowOnboardModal(false);
                      setOnboardData(null);
                    }}
                    className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-neutral-950 font-bold rounded transition-colors cursor-pointer"
                  >
                    Done
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

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
