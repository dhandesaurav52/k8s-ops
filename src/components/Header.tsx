import React from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Menu,
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
  onToggleMobileSidebar: () => void;
  isCloudConnected: boolean;
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
  onToggleMobileSidebar,
  isCloudConnected,
}) => {
  const selectedCluster = clusters.find((c) => c.cluster_id === selectedClusterId);

  return (
    <header className="border-b border-neutral-800 bg-neutral-950 text-neutral-200 sticky top-0 z-30 select-none font-mono">
      <div className="px-4 py-2 flex items-center justify-between gap-3 text-xs">
        {/* Left: Mobile Menu Toggle & Scope Selector */}
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleMobileSidebar}
            className="lg:hidden p-1.5 bg-neutral-900 border border-neutral-800 rounded text-neutral-400 hover:text-neutral-100"
            title="Toggle Sidebar"
          >
            <Menu className="w-4 h-4" />
          </button>

          {/* Cluster Switcher */}
          <div className="relative group">
            <div className="flex items-center gap-1.5 bg-neutral-900 border border-neutral-800 hover:border-neutral-700 px-2.5 py-1 rounded cursor-pointer transition-colors">
              <Server className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-neutral-200 font-medium">
                {selectedClusterId === 'ALL'
                  ? 'ALL CLUSTERS'
                  : selectedCluster?.name || selectedClusterId}
              </span>
              <ChevronDown className="w-3 h-3 text-neutral-500" />
            </div>

            {/* Dropdown Menu */}
            <div className="absolute left-0 top-full mt-1 w-64 bg-neutral-900 border border-neutral-800 rounded shadow-2xl py-1 hidden group-hover:block z-50">
              <div className="px-2.5 py-1 text-[10px] text-neutral-500 uppercase tracking-wider border-b border-neutral-800 font-semibold">
                SELECT CLUSTER SCOPE
              </div>
              <button
                onClick={() => onSelectCluster('ALL')}
                className={`w-full text-left px-2.5 py-1.5 text-xs flex items-center justify-between hover:bg-neutral-800 ${
                  selectedClusterId === 'ALL'
                    ? 'text-cyan-400 font-bold bg-neutral-800/50'
                    : 'text-neutral-300'
                }`}
              >
                <span>ALL CLUSTERS ({clusters.length})</span>
                {selectedClusterId === 'ALL' && <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />}
              </button>
              {clusters.map((c) => (
                <button
                  key={c.cluster_id}
                  onClick={() => onSelectCluster(c.cluster_id)}
                  className={`w-full text-left px-2.5 py-1.5 text-xs flex items-center justify-between hover:bg-neutral-800 ${
                    selectedClusterId === c.cluster_id
                      ? 'text-cyan-400 font-bold bg-neutral-800/50'
                      : 'text-neutral-300'
                  }`}
                >
                  <div className="truncate">
                    <div className="truncate text-neutral-200 font-semibold">{c.name}</div>
                    <div className="text-[10px] text-neutral-500">
                      {c.kubernetes_version} • {c.node_count} nodes
                    </div>
                  </div>
                  {selectedClusterId === c.cluster_id && (
                    <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 ml-1 shrink-0" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Cloud API Connection Indicator Badge */}
          <div className="hidden sm:flex items-center gap-1.5 px-2 py-0.5 bg-neutral-900 border border-neutral-800 rounded text-[11px]">
            <span
              className={`w-2 h-2 rounded-full ${
                isCloudConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'
              }`}
            />
            <span className={isCloudConnected ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>
              {isCloudConnected ? 'API CONNECTED' : 'API OFFLINE'}
            </span>
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
              placeholder="Search incidents, pods, namespaces, categories..."
              className="w-full bg-neutral-900 border border-neutral-800 rounded pl-8 pr-3 py-1 text-xs text-neutral-200 placeholder:text-neutral-600 focus:outline-none focus:border-cyan-500 transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => onSearchChange('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-neutral-300 text-[10px]"
              >
                CLEAR
              </button>
            )}
          </div>
        </div>

        {/* Right: Telemetry Counts & Controls */}
        <div className="flex items-center gap-2">
          {/* Active Incidents Badges */}
          <div className="flex items-center gap-1.5">
            {criticalIncidentCount > 0 && (
              <div className="flex items-center gap-1 bg-red-950 border border-red-800 text-red-400 px-2 py-0.5 rounded text-xs font-bold animate-pulse">
                <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
                <span>{criticalIncidentCount} CRITICAL</span>
              </div>
            )}
            <div className="flex items-center gap-1 bg-neutral-900 border border-neutral-800 text-amber-400 px-2 py-0.5 rounded text-xs font-semibold">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span>{activeIncidentCount} ACTIVE</span>
            </div>
          </div>

          <div className="h-5 w-px bg-neutral-800 hidden sm:block" />

          {/* Trigger Simulation Button */}
          <button
            onClick={onOpenSimulateModal}
            className="flex items-center gap-1 bg-cyan-950 text-cyan-300 hover:bg-cyan-900 border border-cyan-800 px-2.5 py-1 rounded text-xs font-semibold transition-colors cursor-pointer"
            title="Inject simulated K8s failure"
          >
            <PlusCircle className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden lg:inline">INJECT SIGNAL</span>
          </button>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            className="p-1.5 bg-neutral-900 border border-neutral-800 text-neutral-400 hover:text-neutral-100 hover:border-neutral-700 rounded transition-colors cursor-pointer"
            title="Refresh cluster telemetry"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
          </button>

          {/* Theme Toggle */}
          <button
            onClick={onToggleDarkMode}
            className="p-1.5 bg-neutral-900 border border-neutral-800 text-neutral-400 hover:text-neutral-100 hover:border-neutral-700 rounded transition-colors cursor-pointer"
            title="Toggle Theme"
          >
            {darkMode ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5 text-cyan-400" />}
          </button>
        </div>
      </div>
    </header>
  );
};
