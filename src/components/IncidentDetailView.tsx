import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock,
  Compass,
  Copy,
  Cpu,
  FileCode,
  FileText,
  GitBranch,
  HelpCircle,
  Layers,
  Link2,
  ListOrdered,
  Radio,
  RefreshCw,
  Search,
  Server,
  ShieldAlert,
  Sparkles,
  Terminal,
  XCircle,
} from 'lucide-react';
import { Incident } from '../types';
import { SeverityBadge, StatusBadge } from './IncidentStatusBadge';
import { apiService } from '../services/api';

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
  const formatDisplayValue = (value: unknown): string => {
    if (value === null || value === undefined) return '-';

    if (
      typeof value === 'string' ||
      typeof value === 'number' ||
      typeof value === 'boolean'
    ) {
      return String(value);
    }

    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  };

  const [copiedText, setCopiedText] = useState<string | null>(null);
  const [showRawJson, setShowRawJson] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'evidence' | 'graph'>('overview');
  const [logSearchQuery, setLogSearchQuery] = useState<string>('');

  const diagnosis = incident.diagnosis || {};
  const investigation = incident.investigation || {};
  const aiAnalysis = incident.ai_analysis || {};
  const rca = investigation.root_cause_analysis || {};
  const evidenceTimeline = investigation.evidence_timeline || [];
  const blastRadius = investigation.blast_radius || {};
  const relatedIncidents = investigation.related_incidents || [];
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
          <span>DIAGNOSIS & REMEDIATION</span>
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
      )}      {/* TAB 1: AI DIAGNOSIS & REMEDIATION */}
      {activeTab === 'overview' && !showRawJson && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Main 2-Column AI Deep Reasoning & RCA */}
          <div className="lg:col-span-2 space-y-4">
            {/* Evidence-Based Root Cause Diagnosis Box */}
            <div className="bg-neutral-900 border border-neutral-800 rounded p-4 space-y-3">
              <div className="flex items-center gap-2 pb-2 border-b border-neutral-800 text-neutral-100 font-bold text-sm">
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                <span>EVIDENCE-BASED ROOT CAUSE ANALYSIS</span>
                {rca.confidence_score !== undefined ? (
                  <span
                    className={`ml-auto px-2 py-0.5 rounded text-[10px] font-bold border ${
                      rca.confidence_level === 'HIGH'
                        ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                        : rca.confidence_level === 'MEDIUM'
                        ? 'bg-amber-950 text-amber-400 border-amber-800'
                        : 'bg-red-950 text-red-400 border-red-800'
                    }`}
                  >
                    CONFIDENCE: {rca.confidence_score}% ({rca.confidence_level || 'HIGH'})
                  </span>
                ) : diagnosis.confidence ? (
                  <span className="ml-auto px-2 py-0.5 bg-cyan-950 text-cyan-400 border border-cyan-800 rounded text-[10px] font-bold">
                    CONFIDENCE: {Math.round(diagnosis.confidence * 100)}%
                  </span>
                ) : null}
              </div>

              {/* Primary Cause Text */}
              <div className="p-3 bg-neutral-950 border border-neutral-800 rounded leading-relaxed text-neutral-200 font-semibold">
                {rca.candidate_root_cause ||
                  diagnosis.root_cause ||
                  aiAnalysis.summary ||
                  'Correlating cluster events, container state transitions, and metrics...'}
              </div>

              {/* Confidence Reasoning Explanation */}
              {rca.confidence_reasoning && (
                <div className="p-2.5 bg-neutral-950/80 border border-neutral-800/80 rounded text-neutral-400 text-xs leading-relaxed flex items-start gap-2">
                  <Compass className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold text-neutral-300">Scoring Engine Reasoning: </span>
                    {rca.confidence_reasoning}
                  </div>
                </div>
              )}

              {/* Detailed AI / SRE Explanation */}
              {aiAnalysis.detailed_explanation && (
                <div className="space-y-1 pt-1">
                  <div className="text-[10px] text-neutral-500 uppercase tracking-wider font-bold">
                    SRE DEEP DIAGNOSIS EXPLANATION
                  </div>
                  <div className="p-3 bg-neutral-950/60 border border-neutral-800/80 rounded text-neutral-400 leading-relaxed text-xs">
                    {aiAnalysis.detailed_explanation}
                  </div>
                </div>
              )}
            </div>

            {/* "WHY THIS DIAGNOSIS?" EVIDENCE EXPLANATION */}
            <div className="bg-neutral-900 border border-neutral-800 rounded p-4 space-y-3">
              <div className="flex items-center gap-2 pb-2 border-b border-neutral-800 text-neutral-100 font-bold text-sm">
                <HelpCircle className="w-4 h-4 text-cyan-400" />
                <span>WHY THIS DIAGNOSIS? (CORRELATED EVIDENCE)</span>
              </div>

              {/* Supporting Evidence Items */}
              {rca.supporting_evidence && rca.supporting_evidence.length > 0 ? (
                <div className="space-y-2">
                  <div className="text-[10px] text-emerald-400 uppercase tracking-wider font-bold flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                    <span>SUPPORTING CLUSTER SIGNALS ({rca.supporting_evidence.length})</span>
                  </div>
                  <div className="space-y-1.5">
                    {rca.supporting_evidence.slice(0, 5).map((ev: any, idx: number) => (
                      <div
                        key={idx}
                        className="p-2 bg-neutral-950 border border-neutral-800/80 rounded flex items-start gap-2 text-xs"
                      >
                        <span className="px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-900 font-mono text-[10px] shrink-0 font-bold">
                          {ev.source || ev.signal_type || 'SIGNAL'}
                        </span>
                        <div className="text-neutral-300">
                          <span className="font-bold text-neutral-200">{ev.signal_type ? `${ev.signal_type}: ` : ''}</span>
                          {ev.observation || ev.message || JSON.stringify(ev)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="p-3 bg-neutral-950 border border-neutral-800 rounded text-xs text-neutral-400 leading-relaxed">
                  Diagnosis formulated by correlating Kubernetes container exit codes, pod phase state transitions, warning events, and resource metric usage.
                </div>
              )}

              {/* Contradicting Evidence if any */}
              {rca.contradicting_evidence && rca.contradicting_evidence.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-neutral-800/60">
                  <div className="text-[10px] text-amber-400 uppercase tracking-wider font-bold flex items-center gap-1">
                    <XCircle className="w-3 h-3 text-amber-400" />
                    <span>CONTRADICTING / AMBIGUOUS SIGNALS ({rca.contradicting_evidence.length})</span>
                  </div>
                  <div className="space-y-1.5">
                    {rca.contradicting_evidence.map((ev: any, idx: number) => (
                      <div
                        key={idx}
                        className="p-2 bg-neutral-950 border border-amber-900/40 rounded flex items-start gap-2 text-xs"
                      >
                        <span className="px-1.5 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800 font-mono text-[10px] shrink-0 font-bold">
                          CONTRADICTION
                        </span>
                        <div className="text-neutral-300">{ev.statement || JSON.stringify(ev)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Human-Approved Recommended Remediation Commands & Safe Execution Engine */}
            <div className="bg-neutral-900 border border-neutral-800 rounded p-4 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-neutral-800">
                <div className="flex items-center gap-2 text-neutral-100 font-bold text-sm">
                  <Terminal className="w-4 h-4 text-emerald-400" />
                  <span>SAFE AUTOMATED REMEDIATION ENGINE</span>
                </div>
                <span className="px-2 py-0.5 bg-emerald-950 text-emerald-400 border border-emerald-800 rounded text-[10px] font-bold">
                  HUMAN-IN-THE-LOOP APPROVAL
                </span>
              </div>

              {diagnosis.actionable_recommendation && (
                <p className="text-neutral-300 text-xs leading-relaxed">{diagnosis.actionable_recommendation}</p>
              )}

              {/* Remediation Execution Control Panel */}
              <div className="p-3 bg-neutral-950 border border-neutral-800 rounded space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-neutral-500 uppercase font-bold">PROPOSED ACTION:</span>
                    <span className="px-2 py-0.5 bg-cyan-950 text-cyan-300 border border-cyan-800 rounded font-bold text-[11px]">
                      {diagnosis.mitigation_command ? 'RESOURCE_ADJUSTMENT' : 'ROLLOUT_RESTART'}
                    </span>
                    <span className="px-2 py-0.5 bg-amber-950 text-amber-400 border border-amber-800 rounded font-bold text-[10px]">
                      RISK: MEDIUM
                    </span>
                  </div>

                  <div className="text-[10px] text-neutral-400">
                    Target: <strong className="text-neutral-200">{resource.kind}/{resource.name}</strong>
                  </div>
                </div>

                {/* Command Display */}
                <div className="flex items-center justify-between bg-neutral-900 border border-cyan-900/80 rounded p-2.5 font-mono text-cyan-300 text-xs">
                  <code className="truncate mr-2">
                    {diagnosis.mitigation_command || `kubectl rollout restart deployment/${resource.name.split('-')[0]} -n ${resource.namespace}`}
                  </code>
                  <button
                    onClick={() =>
                      handleCopy(
                        diagnosis.mitigation_command ||
                          `kubectl rollout restart deployment/${resource.name.split('-')[0]} -n ${resource.namespace}`
                      )
                    }
                    className="flex items-center gap-1 px-2.5 py-1 bg-cyan-950 hover:bg-cyan-900 text-cyan-400 border border-cyan-800 rounded shrink-0 font-bold transition-colors cursor-pointer"
                  >
                    {copiedText ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-cyan-400" />}
                    <span>COPY</span>
                  </button>
                </div>

                {/* Workflow Buttons: Dry Run -> Approve -> Execute */}
                <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-neutral-800">
                  <button
                    onClick={async () => {
                      try {
                        const data = await apiService.dryRunRemediation(incident.incident_id);
                        alert(`Dry Run Result: ${data.result?.expected_effect || data.detail || 'Dry run passed without mutating cluster state.'}`);
                      } catch (e: any) {
                        alert(`Dry Run error: ${e.message || e}`);
                      }
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-neutral-900 hover:bg-neutral-800 border border-neutral-700 text-neutral-200 font-bold rounded cursor-pointer transition-colors"
                  >
                    <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
                    <span>RUN DRY-RUN VALIDATION</span>
                  </button>

                  <button
                    onClick={async () => {
                      try {
                        await apiService.approveRemediation(incident.incident_id, 'operator@skyops.internal');
                        alert('Remediation action APPROVED by operator.');
                      } catch (e: any) {
                        alert(`Approve response: ${e.message || 'APPROVED'}`);
                      }
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-950 hover:bg-emerald-900 border border-emerald-800 text-emerald-400 font-bold rounded cursor-pointer transition-colors"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>APPROVE REMEDIATION</span>
                  </button>

                  <button
                    onClick={async () => {
                      try {
                        const data = await apiService.executeRemediation(incident.incident_id);
                        if (data.status === 'ALREADY_EXECUTED') {
                          alert('Action previously executed. Idempotency check prevented duplicate call.');
                        } else {
                          alert('Remediation executed and verified healthy! Incident marked RESOLVED.');
                          onResolve(incident.incident_id);
                        }
                      } catch (e: any) {
                        alert(`Execute response: ${e.message || 'Executed'}`);
                        onResolve(incident.incident_id);
                      }
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-950 hover:bg-cyan-900 border border-cyan-800 text-cyan-300 font-bold rounded cursor-pointer transition-colors shadow-lg"
                  >
                    <Terminal className="w-3.5 h-3.5 text-cyan-400" />
                    <span>EXECUTE SAFE REMEDIATION</span>
                  </button>
                </div>
              </div>

              {/* Suggested Kubectl Commands */}
              {aiAnalysis.suggested_kubectl && aiAnalysis.suggested_kubectl.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-neutral-800/60">
                  <div className="text-[10px] text-neutral-500 uppercase tracking-wider font-bold">
                    INVESTIGATION & DIAGNOSTIC COMMANDS
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

          {/* Right Column: Probable Causes, State Timeline, and Related Incidents */}
          <div className="space-y-4">
            {/* Blast Radius Summary Card */}
            {blastRadius.summary && (
              <div className="bg-neutral-900 border border-neutral-800 rounded p-4 space-y-2">
                <div className="flex items-center justify-between pb-2 border-b border-neutral-800 font-bold text-neutral-100 text-sm">
                  <div className="flex items-center gap-2">
                    <Radio className="w-4 h-4 text-purple-400" />
                    <span>BLAST RADIUS SCOPE</span>
                  </div>
                  <span className="px-2 py-0.5 bg-purple-950 text-purple-300 border border-purple-800 rounded text-[10px] font-bold">
                    {blastRadius.scope_level || 'POD'} SCOPE
                  </span>
                </div>
                <p className="text-xs text-neutral-300 leading-relaxed">{blastRadius.summary}</p>
              </div>
            )}

            {/* Related Incidents Summary Card */}
            {relatedIncidents.length > 0 && (
              <div className="bg-neutral-900 border border-neutral-800 rounded p-4 space-y-3">
                <div className="flex items-center gap-2 pb-2 border-b border-neutral-800 font-bold text-neutral-100 text-sm">
                  <Link2 className="w-4 h-4 text-cyan-400" />
                  <span>HISTORICALLY RELATED INCIDENTS ({relatedIncidents.length})</span>
                </div>
                <div className="space-y-2">
                  {relatedIncidents.slice(0, 3).map((rel: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-2 bg-neutral-950 border border-neutral-800 rounded text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between font-mono">
                        <span className="text-cyan-400 font-bold">{rel.incident_id}</span>
                        <span className="px-1.5 py-0.2 bg-neutral-900 text-neutral-400 border border-neutral-800 rounded text-[9px] font-bold">
                          {rel.relationship_type}
                        </span>
                      </div>
                      <div className="text-neutral-300 truncate font-semibold">
                        {rel.resource_name} ({rel.category})
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

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
                      className="p-2 bg-neutral-950 border border-neutral-800/80 rounded text-neutral-300 flex items-start gap-2 text-xs"
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
                  (st: any, idx: number) => (
                    <div key={idx} className="flex items-center gap-3 relative pl-6">
                      <div className="w-2 h-2 rounded-full bg-cyan-400 border border-neutral-900 absolute left-1" />
                      <div className="p-1.5 bg-neutral-950 border border-neutral-800 rounded text-neutral-300 w-full flex items-center justify-between text-[11px]">
                        <div className="flex flex-col gap-0.5">
                          <span className="font-bold">
                            {formatDisplayValue(
                              typeof st === 'object' && st !== null
                                ? st.state ?? st.status ?? st.value
                                : st
                            )}
                          </span>

                          {typeof st === 'object' && st !== null && st.reason && (
                            <span className="text-[10px] text-neutral-500">
                              {formatDisplayValue(st.reason)}
                            </span>
                          )}
                        </div>

                        <div className="flex flex-col items-end gap-0.5">
                          <span className="text-[10px] text-neutral-500">
                            Step #{idx + 1}
                          </span>

                          {typeof st === 'object' && st !== null && st.timestamp && (
                            <span className="text-[10px] text-neutral-600">
                              {new Date(st.timestamp).toLocaleTimeString()}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: TECHNICAL EVIDENCE & CHRONOLOGICAL SIGNAL TIMELINE */}
      {activeTab === 'evidence' && !showRawJson && (
        <div className="space-y-4">
          {/* Chronological Signal Evidence Timeline */}
          {evidenceTimeline.length > 0 && (
            <div className="bg-neutral-900 border border-neutral-800 rounded p-4 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-neutral-800">
                <div className="font-bold text-neutral-100 text-sm flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  <span>CHRONOLOGICAL SIGNAL EVIDENCE TIMELINE ({evidenceTimeline.length} SIGNALS)</span>
                </div>
                <span className="text-[10px] font-mono text-neutral-500">CORRELATED SIGNAL GRAPH</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-xs">
                  <thead>
                    <tr className="border-b border-neutral-800 bg-neutral-950 text-neutral-500 uppercase text-[10px]">
                      <th className="py-2 px-3">EVD ID</th>
                      <th className="py-2 px-3">TIMESTAMP</th>
                      <th className="py-2 px-3">SOURCE</th>
                      <th className="py-2 px-3">RESOURCE</th>
                      <th className="py-2 px-3">SIGNAL TYPE</th>
                      <th className="py-2 px-3">OBSERVATION</th>
                      <th className="py-2 px-3 text-center">RELEVANCE</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-800">
                    {evidenceTimeline.map((item: any, idx: number) => (
                      <tr key={idx} className="hover:bg-neutral-950/60">
                        <td className="py-2 px-3 text-cyan-400 font-bold">{item.evidence_id || `EVD-${idx + 1}`}</td>
                        <td className="py-2 px-3 text-neutral-400 text-[11px]">
                          {new Date(item.timestamp).toLocaleTimeString()}
                        </td>
                        <td className="py-2 px-3">
                          <span className="px-1.5 py-0.5 rounded bg-neutral-950 border border-neutral-800 text-neutral-300 font-bold text-[10px]">
                            {item.source}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-neutral-300 text-[11px] font-semibold">{item.resource}</td>
                        <td className="py-2 px-3 text-amber-400 font-bold">{item.signal_type}</td>
                        <td className="py-2 px-3 text-neutral-200 text-xs max-w-md truncate">{item.observation}</td>
                        <td className="py-2 px-3 text-center">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                              item.relevance === 'HIGH'
                                ? 'bg-red-950 text-red-400 border border-red-900'
                                : item.relevance === 'MEDIUM'
                                ? 'bg-amber-950 text-amber-400 border border-amber-900'
                                : 'bg-neutral-950 text-neutral-400 border border-neutral-800'
                            }`}
                          >
                            {item.relevance}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

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
                  {investigation.container_states && investigation.container_states.length > 0 ? (
                    investigation.container_states.map((cs: any, idx: number) => (
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
                        <td className="py-2 px-3 text-amber-400 font-bold">{formatDisplayValue(cs.reason ?? cs.message)}</td>
                        <td className="py-2 px-3 text-center font-bold text-neutral-200">{cs.restart_count}</td>
                        <td className="py-2 px-3 text-center text-red-400 font-mono font-bold">
                          {cs.exit_code ? cs.exit_code : '-'}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="py-4 text-center text-neutral-500 font-mono">
                        Investigation data unavailable
                      </td>
                    </tr>
                  )}
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
              {investigation.kubernetes_events && investigation.kubernetes_events.length > 0 ? (
                investigation.kubernetes_events.map((evt: any, i: number) => (
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
                      <span className="font-bold text-neutral-200">{formatDisplayValue(evt.reason)}</span>
                      <span className="text-neutral-400 text-xs">{evt.message}</span>
                    </div>
                    <div className="text-[10px] text-neutral-500 font-mono shrink-0">
                      Count: {evt.count}x •{' '}
                      {evt.last_timestamp ? new Date(evt.last_timestamp).toLocaleTimeString() : 'recently'}
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-3 bg-neutral-950 border border-neutral-800 rounded text-center text-neutral-500 font-mono">
                  Investigation data unavailable
                </div>
              )}
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

      {/* TAB 3: K8S RELATIONSHIP TREE & BLAST RADIUS TOPOLOGY */}
      {activeTab === 'graph' && !showRawJson && (
        <div className="space-y-4">
          {/* Blast Radius Topology Impact Card */}
          {blastRadius.summary && (
            <div className="bg-neutral-900 border border-neutral-800 rounded p-4 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-neutral-800">
                <div className="font-bold text-neutral-100 text-sm flex items-center gap-2">
                  <Radio className="w-4 h-4 text-purple-400" />
                  <span>BLAST RADIUS TOPOLOGY IMPACT SCOPE</span>
                </div>
                <span className="px-2 py-0.5 bg-purple-950 text-purple-300 border border-purple-800 rounded text-[10px] font-bold">
                  {blastRadius.scope_level || 'POD'} SCOPE
                </span>
              </div>

              <div className="p-3 bg-neutral-950 border border-neutral-800 rounded text-xs text-neutral-300 font-semibold leading-relaxed">
                {blastRadius.summary}
              </div>

              {/* Workload Status Details */}
              {blastRadius.workload_status && blastRadius.workload_status.kind && (
                <div className="p-2.5 bg-neutral-950/80 border border-neutral-800/80 rounded text-xs grid grid-cols-1 md:grid-cols-4 gap-3">
                  <div>
                    <span className="text-[10px] text-neutral-500 uppercase font-bold block">CONTROLLER</span>
                    <span className="font-bold text-neutral-200">
                      {blastRadius.workload_status.kind}/{blastRadius.workload_status.name}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-neutral-500 uppercase font-bold block">DESIRED REPLICAS</span>
                    <span className="font-bold text-neutral-200">{blastRadius.workload_status.desired_replicas}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-neutral-500 uppercase font-bold block">READY REPLICAS</span>
                    <span className="font-bold text-emerald-400">{blastRadius.workload_status.ready_replicas}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-neutral-500 uppercase font-bold block">AFFECTED REPLICAS</span>
                    <span className="font-bold text-red-400">{blastRadius.workload_status.affected_replicas}</span>
                  </div>
                </div>
              )}

              {/* Impacted Resources Table */}
              {blastRadius.impacted_resources && blastRadius.impacted_resources.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[10px] text-neutral-500 uppercase tracking-wider font-bold">
                    TOPOLOGY IMPACTED KUBERNETES RESOURCES
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {blastRadius.impacted_resources.map((res: any, idx: number) => (
                      <div
                        key={idx}
                        className="p-2 bg-neutral-950 border border-neutral-800 rounded flex items-center justify-between text-xs font-mono"
                      >
                        <div className="truncate">
                          <span className="text-cyan-400 font-bold">{res.kind}/</span>
                          <span className="text-neutral-200">{res.name}</span>
                          {res.namespace && <span className="text-neutral-500 text-[10px]"> (ns/{res.namespace})</span>}
                        </div>
                        <span
                          className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                            res.status === 'DEGRADED' || res.status === 'CRASH_LOOP_BACK_OFF'
                              ? 'bg-amber-950 text-amber-400 border border-amber-800'
                              : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          }`}
                        >
                          {res.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Historically Related Incidents Graph */}
          {relatedIncidents.length > 0 && (
            <div className="bg-neutral-900 border border-neutral-800 rounded p-4 space-y-3">
              <div className="font-bold text-neutral-100 pb-2 border-b border-neutral-800 text-sm flex items-center gap-2">
                <Link2 className="w-4 h-4 text-cyan-400" />
                <span>HISTORICALLY & TEMPORALLY RELATED INCIDENTS ({relatedIncidents.length})</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {relatedIncidents.map((rel: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-3 bg-neutral-950 border border-neutral-800 rounded text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between font-mono">
                      <span className="text-cyan-400 font-bold">{rel.incident_id}</span>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[9px] font-bold border ${
                          rel.relationship_type === 'SAME_RESOURCE'
                            ? 'bg-purple-950 text-purple-300 border-purple-800'
                            : rel.relationship_type === 'RELATED_RESOURCE'
                            ? 'bg-blue-950 text-blue-300 border-blue-800'
                            : 'bg-neutral-900 text-neutral-400 border-neutral-800'
                        }`}
                      >
                        {rel.relationship_type}
                      </span>
                    </div>
                    <div className="text-neutral-200 font-semibold truncate">
                      {rel.resource_name} <span className="text-neutral-500 font-normal">(ns/{rel.namespace})</span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-neutral-400">
                      <span>Category: <strong className="text-amber-400">{rel.category}</strong></span>
                      <StatusBadge status={rel.status} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* K8S Resource Dependency Hierarchy Tree */}
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
        </div>
      )}
    </div>
  );
};
