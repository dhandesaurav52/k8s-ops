import React, { useState } from 'react';
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock,
  Copy,
  Cpu,
  FileCode,
  FileText,
  GitBranch,
  Layers,
  ListOrdered,
  RefreshCw,
  Search,
  Server,
  ShieldAlert,
  Sparkles,
  Terminal,
} from 'lucide-react';
import { Incident } from '../types';
import { SeverityBadge, StatusBadge } from './IncidentStatusBadge';

interface IncidentDetailViewProps {
  incident: Incident;
  onBack: () => void;
  onResolve: (incidentId: string) => void;
  onReanalyze?: (incidentId: string) => void;
}

export const IncidentDetailView: React.FC<IncidentDetailViewProps> = ({
  incident,
  onBack,
  onResolve,
  onReanalyze,
}) => {
  const [copiedText, setCopiedText] = useState<string | null>(null);
  const [showRawJson, setShowRawJson] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'evidence' | 'graph'>('overview');
  const [logSearchQuery, setLogSearchQuery] = useState<string>('');

  const diagnosis = incident.diagnosis || {};
  const investigation = incident.investigation || {};
  const aiAnalysis = incident.ai_analysis || {};
  const resource = incident.resource || {
    kind: 'Pod',
    namespace: 'default',
    name: 'unknown',
    uid: 'unknown',
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(text);
    setTimeout(() => setCopiedText(null), 2000);
  };

  const isResolved = incident.status === 'RESOLVED';

  const rawLogs = investigation.recent_logs || [];
  const filteredLogs = rawLogs.filter((log: string) =>
    logSearchQuery ? log.toLowerCase().includes(logSearchQuery.toLowerCase()) : true
  );

  return (
    <div className="space-y-4 font-mono text-xs text-neutral-200 select-none">
      {/* Top Breadcrumb & Control Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-neutral-900 border border-neutral-800 p-2.5 rounded shadow">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-neutral-950 hover:bg-neutral-800 border border-neutral-700 rounded text-neutral-200 font-semibold transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>BACK TO INCIDENTS</span>
          </button>

          <div className="h-4 w-px bg-neutral-800" />

          <div className="flex items-center gap-2">
            <span className="text-cyan-400 font-bold text-sm">{incident.incident_id}</span>
            <span className="text-neutral-500">•</span>
            <span className="text-neutral-400">cluster/{incident.cluster_id}</span>
          </div>
        </div>

        {/* Header Action Buttons */}
        <div className="flex items-center gap-2">
          {!isResolved && (
            <button
              onClick={() => onResolve(incident.incident_id)}
              className="flex items-center gap-1.5 px-3 py-1 bg-emerald-950 text-emerald-400 hover:bg-emerald-900 border border-emerald-800 rounded font-bold transition-colors cursor-pointer shadow-lg"
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>MARK RESOLVED</span>
            </button>
          )}

          <button
            onClick={() => setShowRawJson(!showRawJson)}
            className={`flex items-center gap-1 px-2.5 py-1 border rounded transition-colors cursor-pointer ${
              showRawJson
                ? 'bg-cyan-950 text-cyan-400 border-cyan-800 font-bold'
                : 'bg-neutral-950 text-neutral-400 border-neutral-800 hover:border-neutral-700'
            }`}
          >
            <FileCode className="w-3.5 h-3.5" />
            <span>RAW JSON</span>
          </button>
        </div>
      </div>

      {/* Flagship Incident Banner */}
      <div className="bg-neutral-900 border border-neutral-800 rounded p-4 shadow-2xl relative overflow-hidden">
        {/* Top Status Bar */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-800 pb-3 mb-3">
          <div className="flex items-center gap-2.5">
            <SeverityBadge severity={incident.severity} className="text-xs px-2 py-0.5" />
            <StatusBadge status={incident.status} className="text-xs px-2 py-0.5" />
            <span className="px-2 py-0.5 bg-neutral-950 border border-neutral-800 rounded text-neutral-300 font-bold">
              {incident.category}
            </span>
            <span className="text-neutral-400">
              Occurrences: <strong className="text-neutral-200">{incident.occurrences}x</strong>
            </span>
          </div>

          <div className="flex items-center gap-3 text-[11px] text-neutral-400">
            <span>
              First seen: <strong className="text-neutral-300">{new Date(incident.first_seen).toLocaleString()}</strong>
            </span>
            <span>
              Last seen: <strong className="text-neutral-300">{new Date(incident.last_seen).toLocaleString()}</strong>
            </span>
          </div>
        </div>

        {/* Target Resource Summary */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 bg-neutral-950 border border-neutral-800 p-3 rounded">
          <div>
            <div className="text-[10px] text-neutral-500 uppercase">AFFECTED K8S RESOURCE</div>
            <div className="font-bold text-neutral-100 flex items-center gap-1.5 mt-0.5 text-sm">
              <span className="px-1.5 py-0.2 bg-cyan-950 border border-cyan-800 text-cyan-400 rounded text-[10px]">
                {resource.kind}
              </span>
              <span className="truncate">{resource.name}</span>
            </div>
          </div>

          <div>
            <div className="text-[10px] text-neutral-500 uppercase">NAMESPACE</div>
            <div className="font-semibold text-neutral-200 mt-0.5">ns/{resource.namespace}</div>
          </div>

          <div>
            <div className="text-[10px] text-neutral-500 uppercase">NODE LOCATION</div>
            <div className="font-semibold text-neutral-200 mt-0.5 flex items-center gap-1">
              <Server className="w-3.5 h-3.5 text-neutral-500" />
              {investigation.node_name || 'Unassigned / Pending'}
            </div>
          </div>

          <div>
            <div className="text-[10px] text-neutral-500 uppercase">CURRENT POD STATE</div>
            <div className="font-semibold text-amber-400 mt-0.5 truncate">
              {incident.current_state || 'Unknown'}
            </div>
          </div>
        </div>
      </div>

      {/* View Tabs */}
      <div className="flex items-center gap-1 border-b border-neutral-800 bg-neutral-950 px-1">
        <button
          onClick={() => {
            setActiveTab('overview');
            setShowRawJson(false);
          }}
          className={`flex items-center gap-1.5 px-3 py-2 border-b-2 font-semibold transition-colors cursor-pointer ${
            activeTab === 'overview' && !showRawJson
              ? 'border-cyan-500 text-cyan-400 bg-neutral-900/50'
              : 'border-transparent text-neutral-400 hover:text-neutral-200'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          <span>AI DIAGNOSIS & REMEDIATION</span>
        </button>

        <button
          onClick={() => {
            setActiveTab('evidence');
            setShowRawJson(false);
          }}
          className={`flex items-center gap-1.5 px-3 py-2 border-b-2 font-semibold transition-colors cursor-pointer ${
            activeTab === 'evidence' && !showRawJson
              ? 'border-cyan-500 text-cyan-400 bg-neutral-900/50'
              : 'border-transparent text-neutral-400 hover:text-neutral-200'
          }`}
        >
          <FileText className="w-3.5 h-3.5 text-neutral-400" />
          <span>TECHNICAL EVIDENCE & LOGS</span>
        </button>

        <button
          onClick={() => {
            setActiveTab('graph');
            setShowRawJson(false);
          }}
          className={`flex items-center gap-1.5 px-3 py-2 border-b-2 font-semibold transition-colors cursor-pointer ${
            activeTab === 'graph' && !showRawJson
              ? 'border-cyan-500 text-cyan-400 bg-neutral-900/50'
              : 'border-transparent text-neutral-400 hover:text-neutral-200'
          }`}
        >
          <GitBranch className="w-3.5 h-3.5 text-neutral-400" />
          <span>K8S RELATIONSHIP TREE</span>
        </button>
      </div>

      {/* RAW JSON VIEW MODAL/PANEL */}
      {showRawJson && (
        <div className="bg-neutral-900 border border-neutral-800 rounded p-3 space-y-2">
          <div className="flex items-center justify-between pb-1 border-b border-neutral-800">
            <span className="font-bold text-cyan-400">Raw Incident Payload (JSON)</span>
            <button
              onClick={() => handleCopy(JSON.stringify(incident, null, 2))}
              className="flex items-center gap-1 px-2 py-0.5 bg-neutral-950 border border-neutral-800 rounded hover:border-neutral-700 text-neutral-300 cursor-pointer"
            >
              {copiedText === JSON.stringify(incident, null, 2) ? (
                <Check className="w-3 h-3 text-emerald-400" />
              ) : (
                <Copy className="w-3 h-3 text-neutral-400" />
              )}
              <span>COPY JSON</span>
            </button>
          </div>
          <pre className="p-3 bg-neutral-950 text-emerald-400 rounded border border-neutral-800 overflow-x-auto text-[11px] max-h-96">
            {JSON.stringify(incident, null, 2)}
          </pre>
        </div>
      )}

      {/* TAB 1: AI DIAGNOSIS & REMEDIATION */}
      {activeTab === 'overview' && !showRawJson && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Main 2-Column AI Deep Reasoning */}
          <div className="lg:col-span-2 space-y-4">
            {/* Root Cause Box */}
            <div className="bg-neutral-900 border border-neutral-800 rounded p-4">
              <div className="flex items-center gap-2 mb-3 pb-2 border-b border-neutral-800 text-neutral-100 font-bold text-sm">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <span>ROOT CAUSE DIAGNOSIS</span>
                {diagnosis.confidence && (
                  <span className="ml-auto px-1.5 py-0.2 bg-cyan-950 text-cyan-400 border border-cyan-800 rounded text-[10px]">
                    CONFIDENCE: {Math.round(diagnosis.confidence * 100)}%
                  </span>
                )}
              </div>

              <div className="p-3 bg-neutral-950 border border-neutral-800 rounded leading-relaxed text-neutral-300">
                {diagnosis.root_cause ||
                  aiAnalysis.summary ||
                  'Analyzing Kubernetes pod event signals...'}
              </div>

              {/* Detailed AI Explanation */}
              {aiAnalysis.detailed_explanation && (
                <div className="mt-3 space-y-1">
                  <div className="text-[10px] text-neutral-500 uppercase tracking-wider">
                    SRE ENGINE EXPLANATION
                  </div>
                  <div className="p-3 bg-neutral-950/60 border border-neutral-800/80 rounded text-neutral-400 leading-relaxed text-xs">
                    {aiAnalysis.detailed_explanation}
                  </div>
                </div>
              )}
            </div>

            {/* Recommended Remediation Commands */}
            <div className="bg-neutral-900 border border-neutral-800 rounded p-4">
              <div className="flex items-center gap-2 mb-3 pb-2 border-b border-neutral-800 text-neutral-100 font-bold text-sm">
                <Terminal className="w-4 h-4 text-cyan-400" />
                <span>RECOMMENDED REMEDIATION</span>
              </div>

              {diagnosis.actionable_recommendation && (
                <p className="text-neutral-300 mb-3">{diagnosis.actionable_recommendation}</p>
              )}

              {/* Executable Mitigation Command Box */}
              {diagnosis.mitigation_command && (
                <div className="space-y-1 mb-3">
                  <div className="text-[10px] text-neutral-500 uppercase tracking-wider">
                    RECOMMENDED FIX COMMAND
                  </div>
                  <div className="flex items-center justify-between bg-neutral-950 border border-cyan-900/80 rounded p-2.5 font-mono text-cyan-300">
                    <code className="truncate mr-2">{diagnosis.mitigation_command}</code>
                    <button
                      onClick={() => handleCopy(diagnosis.mitigation_command!)}
                      className="flex items-center gap-1 px-2.5 py-1 bg-cyan-950 hover:bg-cyan-900 text-cyan-400 border border-cyan-800 rounded shrink-0 font-bold transition-colors cursor-pointer"
                    >
                      {copiedText === diagnosis.mitigation_command ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5 text-cyan-400" />
                      )}
                      <span>COPY</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Suggested Kubectl Commands */}
              {aiAnalysis.suggested_kubectl && aiAnalysis.suggested_kubectl.length > 0 && (
                <div className="space-y-2">
                  <div className="text-[10px] text-neutral-500 uppercase tracking-wider">
                    INVESTIGATION COMMANDS
                  </div>
                  <div className="space-y-1.5">
                    {aiAnalysis.suggested_kubectl.map((cmd: string, idx: number) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between bg-neutral-950 border border-neutral-800 rounded px-2.5 py-1.5 font-mono text-neutral-300 text-[11px]"
                      >
                        <code className="truncate mr-2">{cmd}</code>
                        <button
                          onClick={() => handleCopy(cmd)}
                          className="text-neutral-500 hover:text-neutral-200 text-[10px] cursor-pointer"
                        >
                          {copiedText === cmd ? (
                            <Check className="w-3 h-3 text-emerald-400" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Probable Causes & Timeline */}
          <div className="space-y-4">
            {/* Probable Causes */}
            <div className="bg-neutral-900 border border-neutral-800 rounded p-4">
              <div className="flex items-center gap-2 mb-3 pb-2 border-b border-neutral-800 font-bold text-neutral-100 text-sm">
                <ListOrdered className="w-4 h-4 text-amber-400" />
                <span>PROBABLE CAUSES</span>
              </div>
              <ul className="space-y-2">
                {(aiAnalysis.probable_causes || ['Configuration or resource limits mismatch']).map(
                  (cause: string, i: number) => (
                    <li
                      key={i}
                      className="p-2 bg-neutral-950 border border-neutral-800/80 rounded text-neutral-300 flex items-start gap-2"
                    >
                      <span className="w-4 h-4 rounded-full bg-amber-950 text-amber-400 border border-amber-800/80 flex items-center justify-center text-[10px] shrink-0 font-bold">
                        {i + 1}
                      </span>
                      <span>{cause}</span>
                    </li>
                  )
                )}
              </ul>
            </div>

            {/* Incident State History Timeline */}
            <div className="bg-neutral-900 border border-neutral-800 rounded p-4">
              <div className="flex items-center gap-2 mb-3 pb-2 border-b border-neutral-800 font-bold text-neutral-100 text-sm">
                <Clock className="w-4 h-4 text-cyan-400" />
                <span>STATE TRANSITION TIMELINE</span>
              </div>
              <div className="space-y-2 relative before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-neutral-800">
                {(incident.state_history || ['Pending', incident.current_state]).map(
                  (st: string, idx: number) => (
                    <div key={idx} className="flex items-center gap-3 relative pl-6">
                      <div className="w-2 h-2 rounded-full bg-cyan-400 border border-neutral-900 absolute left-1" />
                      <div className="p-1.5 bg-neutral-950 border border-neutral-800 rounded text-neutral-300 w-full flex items-center justify-between text-[11px]">
                        <span>{st}</span>
                        <span className="text-[10px] text-neutral-500">Step #{idx + 1}</span>
                      </div>
                    </div>
                  )
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: TECHNICAL EVIDENCE & LOGS */}
      {activeTab === 'evidence' && !showRawJson && (
        <div className="space-y-4">
          {/* Container States Matrix */}
          <div className="bg-neutral-900 border border-neutral-800 rounded p-4">
            <div className="font-bold text-neutral-100 mb-3 pb-2 border-b border-neutral-800 text-sm flex items-center gap-2">
              <Cpu className="w-4 h-4 text-cyan-400" />
              <span>CONTAINER STATUS MATRIX</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-xs">
                <thead>
                  <tr className="border-b border-neutral-800 bg-neutral-950 text-neutral-500 uppercase text-[10px]">
                    <th className="py-2 px-3">CONTAINER</th>
                    <th className="py-2 px-3">IMAGE TAG</th>
                    <th className="py-2 px-3">STATE</th>
                    <th className="py-2 px-3">REASON</th>
                    <th className="py-2 px-3 text-center">RESTARTS</th>
                    <th className="py-2 px-3 text-center">EXIT CODE</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800">
                  {(investigation.container_states || [
                    {
                      name: resource.name,
                      image: 'unknown:latest',
                      ready: false,
                      restart_count: incident.occurrences,
                      state_type: 'waiting',
                      reason: incident.category,
                      exit_code: 137,
                    },
                  ]).map((cs: any, idx: number) => (
                    <tr key={idx} className="hover:bg-neutral-950/60">
                      <td className="py-2 px-3 font-bold text-neutral-200">{cs.name}</td>
                      <td className="py-2 px-3 text-neutral-400 text-[11px] truncate max-w-xs">
                        {cs.image}
                      </td>
                      <td className="py-2 px-3">
                        <span className="px-1.5 py-0.5 rounded bg-neutral-950 border border-neutral-800 text-neutral-300">
                          {cs.state_type}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-amber-400 font-bold">{cs.reason || cs.message || '-'}</td>
                      <td className="py-2 px-3 text-center font-bold text-neutral-200">{cs.restart_count}</td>
                      <td className="py-2 px-3 text-center text-red-400 font-mono font-bold">
                        {cs.exit_code ? cs.exit_code : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Kubernetes Events List */}
          <div className="bg-neutral-900 border border-neutral-800 rounded p-4">
            <div className="font-bold text-neutral-100 mb-3 pb-2 border-b border-neutral-800 text-sm flex items-center gap-2">
              <FileText className="w-4 h-4 text-amber-400" />
              <span>CHRONOLOGICAL KUBERNETES EVENTS</span>
            </div>

            <div className="space-y-2">
              {(investigation.kubernetes_events || [
                {
                  type: 'Warning',
                  reason: incident.category,
                  message: incident.current_state,
                  count: incident.occurrences,
                  last_timestamp: incident.last_seen,
                },
              ]).map((evt: any, i: number) => (
                <div
                  key={i}
                  className="p-2.5 bg-neutral-950 border border-neutral-800 rounded flex flex-col md:flex-row items-start md:items-center justify-between gap-2"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        evt.type === 'Warning'
                          ? 'bg-amber-950 text-amber-400 border border-amber-800'
                          : 'bg-blue-950 text-blue-400 border border-blue-800'
                      }`}
                    >
                      {evt.type}
                    </span>
                    <span className="font-bold text-neutral-200">{evt.reason}</span>
                    <span className="text-neutral-400 text-xs">{evt.message}</span>
                  </div>
                  <div className="text-[10px] text-neutral-500 font-mono shrink-0">
                    Count: {evt.count}x •{' '}
                    {evt.last_timestamp ? new Date(evt.last_timestamp).toLocaleTimeString() : 'recently'}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Logs Stream */}
          <div className="bg-neutral-900 border border-neutral-800 rounded p-4 space-y-2">
            <div className="flex items-center justify-between pb-2 border-b border-neutral-800">
              <div className="font-bold text-neutral-100 text-sm flex items-center gap-2">
                <Terminal className="w-4 h-4 text-emerald-400" />
                <span>RECENT CONTAINER LOGS STREAM</span>
              </div>

              <div className="flex items-center gap-2">
                <div className="relative w-48">
                  <Search className="w-3 h-3 absolute left-2 top-1/2 -translate-y-1/2 text-neutral-500" />
                  <input
                    type="text"
                    value={logSearchQuery}
                    onChange={(e) => setLogSearchQuery(e.target.value)}
                    placeholder="Search logs..."
                    className="w-full bg-neutral-950 border border-neutral-800 rounded pl-6 pr-2 py-0.5 text-[11px] text-neutral-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                {rawLogs.length > 0 && (
                  <button
                    onClick={() => handleCopy(rawLogs.join('\n'))}
                    className="flex items-center gap-1 px-2 py-0.5 bg-neutral-950 border border-neutral-800 rounded text-neutral-300 hover:border-neutral-700 cursor-pointer text-[10px]"
                  >
                    {copiedText === rawLogs.join('\n') ? (
                      <Check className="w-3 h-3 text-emerald-400" />
                    ) : (
                      <Copy className="w-3 h-3 text-neutral-400" />
                    )}
                    <span>COPY LOGS</span>
                  </button>
                )}
              </div>
            </div>

            <div className="bg-neutral-950 border border-neutral-800 p-3 rounded font-mono text-emerald-400 text-[11px] space-y-1 max-h-72 overflow-y-auto">
              {filteredLogs.length > 0 ? (
                filteredLogs.map((log: string, i: number) => <div key={i}>{log}</div>)
              ) : (
                <div className="text-neutral-600 italic">No logs available for this container state.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: K8S RELATIONSHIP TREE */}
      {activeTab === 'graph' && !showRawJson && (
        <div className="bg-neutral-900 border border-neutral-800 rounded p-4 space-y-4">
          <div className="font-bold text-neutral-100 pb-2 border-b border-neutral-800 text-sm flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-cyan-400" />
            <span>KUBERNETES RESOURCE DEPENDENCY GRAPH</span>
          </div>

          <div className="p-4 bg-neutral-950 border border-neutral-800 rounded space-y-4">
            {/* Cluster Parent */}
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-cyan-400" />
              <span className="font-bold text-cyan-400">Cluster: {incident.cluster_id}</span>
            </div>

            {/* Namespace Level */}
            <div className="pl-6 border-l-2 border-neutral-800 space-y-3">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-neutral-400" />
                <span className="font-semibold text-neutral-300">Namespace: ns/{resource.namespace}</span>
              </div>

              {/* Deployment / Owner Level */}
              <div className="pl-6 border-l-2 border-neutral-800 space-y-3">
                {resource.owner_references && resource.owner_references.length > 0 ? (
                  resource.owner_references.map((owner, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <Layers className="w-4 h-4 text-purple-400" />
                      <span className="font-semibold text-purple-300">
                        {owner.kind}: {owner.name}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="flex items-center gap-2">
                    <Layers className="w-4 h-4 text-purple-400" />
                    <span className="font-semibold text-purple-300">
                      Workload: Deployment/{resource.name.split('-')[0]}
                    </span>
                  </div>
                )}

                {/* Target Pod Level (Affected) */}
                <div className="pl-6 border-l-2 border-amber-500/80 space-y-2">
                  <div className="p-3 bg-amber-950/40 border border-amber-800/80 rounded flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-amber-400" />
                      <span className="font-bold text-amber-300">
                        {resource.kind}: {resource.name} (TARGET)
                      </span>
                    </div>
                    <StatusBadge status={incident.status} />
                  </div>

                  {/* Node Hosting Level */}
                  <div className="pl-6 border-l-2 border-neutral-800">
                    <div className="p-2 bg-neutral-900 border border-neutral-800 rounded flex items-center gap-2 text-neutral-300">
                      <Server className="w-3.5 h-3.5 text-neutral-400" />
                      <span>Host Node: {investigation.node_name || 'gke-prod-pool-1-8a9d02'}</span>
                      <span className="ml-auto text-[10px] text-emerald-400">Node Status: Ready</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
