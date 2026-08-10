import React, { useEffect, useState } from 'react';
import { Search, Terminal, CheckCircle2, AlertCircle } from 'lucide-react';
import { apiService } from '../services/api';

interface EventStreamConsoleProps {
  clusterId: string;
}

interface TelemetryEvent {
  time: string;
  type: 'INFO' | 'WARNING' | 'SUCCESS' | 'ERROR';
  source: string;
  message: string;
}

export const EventStreamConsole: React.FC<EventStreamConsoleProps> = ({ clusterId }) => {
  const [filterQuery, setFilterQuery] = useState<string>('');
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    Promise.all([
      apiService.fetchAuditRecords(clusterId).catch(() => []),
      apiService.fetchIncidents(clusterId).catch(() => []),
    ]).then(([auditRecords, incidents]) => {
      if (!isMounted) return;

      const generatedEvents: TelemetryEvent[] = [];

      // Transform audit records into telemetry events
      (auditRecords || []).forEach((rec: any) => {
        generatedEvents.push({
          time: rec.timestamp || rec.created_at || new Date().toISOString(),
          type: rec.status === 'SUCCESS' || rec.status === 'APPROVED' ? 'SUCCESS' : rec.status === 'REJECTED' || rec.status === 'FAILED' ? 'ERROR' : 'INFO',
          source: 'Remediation.Audit',
          message: `Action [${rec.action_type || 'REMEDIATION'}] on ${rec.target || rec.incident_id || 'resource'}: ${rec.details || rec.status}`,
        });
      });

      // Transform incident events into telemetry events
      (incidents || []).forEach((inc) => {
        generatedEvents.push({
          time: inc.first_seen || inc.last_seen || new Date().toISOString(),
          type: inc.status === 'RESOLVED' ? 'SUCCESS' : inc.severity === 'CRITICAL' ? 'ERROR' : 'WARNING',
          source: 'Incident.Engine',
          message: `Incident ${inc.incident_id} [${inc.category}] on ${inc.resource?.kind}/${inc.resource?.name} in ns/${inc.resource?.namespace}: ${inc.current_state || inc.status}`,
        });
      });

      // Sort newest first
      generatedEvents.sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());

      setEvents(generatedEvents);
      setLoading(false);
    });

    return () => {
      isMounted = false;
    };
  }, [clusterId]);

  const filtered = events.filter((e) => {
    if (!filterQuery) return true;
    const q = filterQuery.toLowerCase();
    return (
      e.message.toLowerCase().includes(q) ||
      e.source.toLowerCase().includes(q) ||
      e.type.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-4 font-mono text-xs text-neutral-200">
      {/* Telemetry Status Notice */}
      <div className="bg-neutral-900 border border-neutral-800 p-2.5 rounded flex items-center justify-between text-[11px] text-neutral-300">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-cyan-400 shrink-0" />
          <span>Live audit and incident telemetry stream backed by PostgreSQL database.</span>
        </div>
        <span className="text-cyan-400 font-bold">Scope: {clusterId || 'ALL'}</span>
      </div>

      {/* Terminal Stream Console */}
      <div className="bg-neutral-950 border border-neutral-800 rounded shadow-2xl overflow-hidden">
        {/* Console Header Bar */}
        <div className="bg-neutral-900 border-b border-neutral-800 p-2.5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span className="font-bold text-neutral-100">KUBERNETES & AGENT EVENT TELEMETRY STREAM</span>
          </div>

          <div className="relative w-64">
            <Search className="w-3.5 h-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-neutral-500" />
            <input
              type="text"
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              placeholder="Filter logs..."
              className="w-full bg-neutral-950 border border-neutral-800 rounded pl-7 pr-2 py-0.5 text-xs text-neutral-200 focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        {/* Log Lines */}
        <div className="p-3 space-y-1.5 font-mono text-[11px] max-h-96 overflow-y-auto">
          {loading ? (
            <div className="py-8 text-center text-neutral-500">Loading live telemetry stream...</div>
          ) : filtered.length === 0 ? (
            <div className="py-8 text-center text-neutral-500 space-y-1">
              <p className="font-bold text-neutral-400">No telemetry stream events recorded</p>
              <p className="text-[10px]">Events are logged automatically when incidents occur or remediation actions execute.</p>
            </div>
          ) : (
            filtered.map((evt, idx) => (
              <div key={idx} className="flex items-start gap-2 py-0.5 border-b border-neutral-900/60 hover:bg-neutral-900/40">
                <span className="text-neutral-500 shrink-0">{evt.time.replace('T', ' ').substring(0, 19)}</span>
                <span
                  className={`px-1 rounded text-[10px] font-bold shrink-0 ${
                    evt.type === 'WARNING'
                      ? 'bg-amber-950 text-amber-400 border border-amber-800'
                      : evt.type === 'SUCCESS'
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : evt.type === 'ERROR'
                      ? 'bg-red-950 text-red-400 border border-red-800'
                      : 'bg-blue-950 text-blue-400 border border-blue-800'
                  }`}
                >
                  {evt.type}
                </span>
                <span className="text-cyan-400 font-bold shrink-0">[{evt.source}]</span>
                <span className="text-neutral-300">{evt.message}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
