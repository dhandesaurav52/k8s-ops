import React from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Moon,
  PlusCircle,
  RefreshCw,
  Search,
  Server,
  ShieldAlert,
  Sun,
  Terminal,
} from 'lucide-react';
import { ClusterInfo } from '../types';

interface HeaderProps {
  clusters: ClusterInfo[];
  selectedClusterId: string;
  onSelectCluster: (clusterId: string) => void;
  activeIncidentCount: number;
  criticalIncidentCount: number;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  isRefreshing: boolean;
  onRefresh: () => void;
  onOpenSimulateModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  clusters,
  selectedClusterId,
  onSelectCluster,
  activeIncidentCount,
  criticalIncidentCount,
  searchQuery,
  onSearchChange,
  darkMode,
  onToggleDarkMode,
  isRefreshing,
  onRefresh,
  onOpenSimulateModal,
}) => {
  const selectedCluster = clusters.find((c) => c.cluster_id === selectedClusterId);

  return (
    <header className="border-b border-neutral-800 bg-neutral-950 text-neutral-200 sticky top-0 z-30 select-none">
      <div className="mx-auto px-3 py-2 flex items-center justify-between gap-3 text-xs">
        {/* Left: Brand Identity & Status */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded bg-neutral-900 border border-neutral-700 flex items-center justify-center text-cyan-400 font-mono font-bold text-sm shadow-inner">
              <Terminal className="w-4 h-4 text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-1.5 font-mono font-bold tracking-tight text-neutral-100 text-sm">
                SKYOPS
                <span className="text-[10px] font-mono font-normal px-1 py-0.2 bg-cyan-950/80 text-cyan-400 border border-cyan-800/80 rounded">
                  v1.0.0
                </span>
              </div>
              <div className="text-[10px] text-neutral-400 font-mono flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block"></span>
                KUBERNETES INCIDENT INTELLIGENCE
              </div>
            </div>
          </div>

          <div className="h-5 w-px bg-neutral-800 hidden sm:block" />

          {/* Cluster Switcher */}
          <div className="relative group">
            <div className="flex items-center gap-1.5 bg-neutral-900 border border-neutral-800 hover:border-neutral-700 px-2.5 py-1 rounded cursor-pointer transition-colors">
              <Server className="w-3.5 h-3.5 text-neutral-400" />
              <span className="text-neutral-300 font-mono font-medium">
                {selectedClusterId === 'ALL'
                  ? 'ALL CLUSTERS'
                  : selectedCluster?.name || selectedClusterId}
              </span>
              <ChevronDown className="w-3 h-3 text-neutral-500" />
            </div>

            {/* Dropdown Menu */}
            <div className="absolute left-0 top-full mt-1 w-64 bg-neutral-900 border border-neutral-800 rounded shadow-2xl py-1 hidden group-hover:block z-50">
              <div className="px-2 py-1 text-[10px] font-mono text-neutral-500 uppercase tracking-wider border-b border-neutral-800">
                Select Scope
              </div>
              <button
                onClick={() => onSelectCluster('ALL')}
                className={`w-full text-left px-2.5 py-1.5 text-xs font-mono flex items-center justify-between hover:bg-neutral-800 ${
                  selectedClusterId === 'ALL' ? 'text-cyan-400 font-semibold bg-neutral-800/50' : 'text-neutral-300'
                }`}
              >
                <span>ALL CLUSTERS ({clusters.length})</span>
                {selectedClusterId === 'ALL' && <CheckCircle2 className="w-3 h-3 text-cyan-400" />}
              </button>
              {clusters.map((c) => (
                <button
                  key={c.cluster_id}
                  onClick={() => onSelectCluster(c.cluster_id)}
                  className={`w-full text-left px-2.5 py-1.5 text-xs font-mono flex items-center justify-between hover:bg-neutral-800 ${
                    selectedClusterId === c.cluster_id ? 'text-cyan-400 font-semibold bg-neutral-800/50' : 'text-neutral-300'
                  }`}
                >
                  <div className="truncate">
                    <div className="truncate text-neutral-200">{c.name}</div>
                    <div className="text-[10px] text-neutral-500 font-mono">{c.kubernetes_version} • {c.node_count} nodes</div>
                  </div>
                  {selectedClusterId === c.cluster_id && <CheckCircle2 className="w-3 h-3 text-cyan-400 ml-1 shrink-0" />}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Center: Search Input Bar */}
        <div className="flex-1 max-w-md hidden md:block">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search incidents, pods, namespaces, categories, UIDs..."
              className="w-full bg-neutral-900 border border-neutral-800 rounded pl-8 pr-3 py-1 text-xs text-neutral-200 font-mono placeholder:text-neutral-600 focus:outline-none focus:border-cyan-500/80 transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => onSearchChange('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-neutral-300 text-[10px] font-mono"
              >
                CLEAR
              </button>
            )}
          </div>
        </div>

        {/* Right: Telemetry Counts & Action Controls */}
        <div className="flex items-center gap-2">
          {/* Active Incidents Badges */}
          <div className="flex items-center gap-1.5 font-mono">
            {criticalIncidentCount > 0 && (
              <div className="flex items-center gap-1 bg-red-950/80 border border-red-800/80 text-red-400 px-2 py-0.5 rounded text-xs font-semibold animate-pulse">
                <ShieldAlert className="w-3 h-3 text-red-400" />
                <span>{criticalIncidentCount} CRITICAL</span>
              </div>
            )}
            <div className="flex items-center gap-1 bg-neutral-900 border border-neutral-800 text-neutral-300 px-2 py-0.5 rounded text-xs">
              <AlertTriangle className="w-3 h-3 text-amber-400" />
              <span>{activeIncidentCount} ACTIVE</span>
            </div>
          </div>

          <div className="h-5 w-px bg-neutral-800 hidden sm:block" />

          {/* Trigger Simulation Button */}
          <button
            onClick={onOpenSimulateModal}
            className="flex items-center gap-1 bg-cyan-950 text-cyan-300 hover:bg-cyan-900 border border-cyan-800 px-2 py-1 rounded text-xs font-mono font-medium transition-colors"
            title="Inject simulated K8s failure"
          >
            <PlusCircle className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden lg:inline">INJECT SIGNAL</span>
          </button>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            className="p-1.5 bg-neutral-900 border border-neutral-800 text-neutral-400 hover:text-neutral-200 hover:border-neutral-700 rounded transition-colors"
            title="Refresh cluster telemetry"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
          </button>

          {/* Theme Toggle */}
          <button
            onClick={onToggleDarkMode}
            className="p-1.5 bg-neutral-900 border border-neutral-800 text-neutral-400 hover:text-neutral-200 hover:border-neutral-700 rounded transition-colors"
            title="Toggle Theme"
          >
            {darkMode ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5 text-cyan-400" />}
          </button>
        </div>
      </div>
    </header>
  );
};
