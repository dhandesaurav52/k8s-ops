import React, { useEffect, useState } from 'react';
import { X, CheckCircle2, Server, Terminal, Shield, RefreshCw, Activity, Layers, Wifi, Clock } from 'lucide-react';
import { ClusterInfo, Incident } from '../types';
import { apiService } from '../services/api';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  isCloudConnected: boolean;
  clusters: ClusterInfo[];
  incidents: Incident[];
  onRefresh: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  isCloudConnected,
  clusters,
  incidents,
  onRefresh,
}) => {
  const [healthStatus, setHealthStatus] = useState<'CONNECTED' | 'DEGRADED' | 'OFFLINE'>('CONNECTED');
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [lastChecked, setLastChecked] = useState<string | null>(null);
  const [isProbing, setIsProbing] = useState<boolean>(false);

  const runHealthProbe = async () => {
    setIsProbing(true);
    const res = await apiService.checkHealth();
    setHealthStatus(res.status);
    setLatencyMs(res.latencyMs);
    setLastChecked(res.timestamp);
    setIsProbing(false);
  };

  useEffect(() => {
    if (isOpen) {
      runHealthProbe();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-950/80 backdrop-blur-sm font-mono text-xs">
      <div className="w-full max-w-xl bg-neutral-900 border border-neutral-800 rounded-lg shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 border-b border-neutral-800 bg-neutral-950">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded bg-cyan-950 border border-cyan-800 flex items-center justify-center text-cyan-400">
              <Terminal className="w-4 h-4 text-cyan-400" />
            </div>
            <div>
              <div className="font-bold text-neutral-100 text-sm">System & Cloud API Info</div>
              <div className="text-[10px] text-neutral-400">SkyOps Autonomous K8s Remediation Console</div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-neutral-400 hover:text-neutral-100 hover:bg-neutral-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 space-y-4 text-neutral-300">
          {/* Cloud API Real Probe Status Box */}
          <div className="p-3 bg-neutral-950 border border-neutral-800 rounded space-y-2">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-neutral-400 font-bold flex items-center gap-1.5">
                <Wifi className="w-3.5 h-3.5 text-cyan-400" />
                REAL-TIME CLOUD API PROBE
              </span>
              <button
                onClick={runHealthProbe}
                disabled={isProbing}
                className="text-[10px] text-cyan-400 hover:text-cyan-300 font-bold flex items-center gap-1 cursor-pointer"
              >
                <RefreshCw className={`w-3 h-3 ${isProbing ? 'animate-spin' : ''}`} />
                PROBE NOW
              </button>
            </div>

            <div className="flex items-center justify-between text-xs pt-1 border-t border-neutral-900">
              <span className="text-neutral-400">API Status:</span>
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-2 h-2 rounded-full ${
                    healthStatus === 'CONNECTED'
                      ? 'bg-emerald-500 animate-pulse'
                      : healthStatus === 'DEGRADED'
                      ? 'bg-amber-500'
                      : 'bg-red-500'
                  }`}
                />
                <span
                  className={`font-bold ${
                    healthStatus === 'CONNECTED'
                      ? 'text-emerald-400'
                      : healthStatus === 'DEGRADED'
                      ? 'text-amber-400'
                      : 'text-red-400'
                  }`}
                >
                  {healthStatus}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-neutral-400">Latency:</span>
              <span className="font-bold text-neutral-100">
                {latencyMs !== null ? `${latencyMs} ms` : 'Measuring...'}
              </span>
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-neutral-400">Last checked:</span>
              <span className="text-neutral-400 font-mono text-[11px] flex items-center gap-1">
                <Clock className="w-3 h-3 text-neutral-500" />
                {lastChecked ? new Date(lastChecked).toLocaleTimeString() : 'Not probed'}
              </span>
            </div>
          </div>

          {/* Infrastructure Metrics Summary */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-neutral-950 border border-neutral-800 rounded">
              <div className="text-[10px] text-neutral-500 uppercase">REGISTERED CLUSTERS</div>
              <div className="text-lg font-bold text-neutral-100 mt-1">{clusters.length} Active</div>
            </div>

            <div className="p-3 bg-neutral-950 border border-neutral-800 rounded">
              <div className="text-[10px] text-neutral-500 uppercase">RECORDED INCIDENTS</div>
              <div className="text-lg font-bold text-amber-400 mt-1">{incidents.length} Total</div>
            </div>
          </div>

          {/* Architecture Pipeline Summary */}
          <div className="p-3 bg-neutral-950 border border-neutral-800 rounded space-y-1.5 text-[11px]">
            <div className="font-bold text-neutral-200 uppercase text-[10px] border-b border-neutral-800 pb-1 mb-1">
              SKYOPS ARCHITECTURE PIPELINE
            </div>
            <div className="flex justify-between text-neutral-400">
              <span>Agent Watcher:</span>
              <span className="text-emerald-400 font-semibold">Active (Thread-safe K8s Watcher)</span>
            </div>
            <div className="flex justify-between text-neutral-400">
              <span>Outbox Store:</span>
              <span className="text-cyan-400 font-semibold">SQLite / File-backed Queue</span>
            </div>
            <div className="flex justify-between text-neutral-400">
              <span>Cloud Engine:</span>
              <span className="text-neutral-200 font-semibold">FastAPI + Async Outbox Worker</span>
            </div>
            <div className="flex justify-between text-neutral-400">
              <span>AI Diagnosis:</span>
              <span className="text-purple-400 font-semibold">Server-side Gemini 2.5 Flash</span>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-neutral-800 bg-neutral-950 flex items-center justify-between">
          <button
            onClick={onRefresh}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-neutral-800 hover:bg-neutral-700 text-neutral-200 border border-neutral-700 text-xs transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5 text-neutral-400" />
            <span>Force Refresh API Data</span>
          </button>

          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-cyan-950 hover:bg-cyan-900 border border-cyan-800 text-cyan-400 font-bold text-xs transition-colors cursor-pointer"
          >
            Close Window
          </button>
        </div>
      </div>
    </div>
  );
};
