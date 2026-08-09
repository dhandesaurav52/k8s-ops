import React, { useState } from 'react';
import { Radio, Search, Terminal, ArrowUpRight, CheckCircle2, RefreshCw } from 'lucide-react';

interface EventStreamConsoleProps {
  clusterId: string;
}

export const EventStreamConsole: React.FC<EventStreamConsoleProps> = ({ clusterId }) => {
  const [filterQuery, setFilterQuery] = useState<string>('');

  const sampleEvents = [
    { time: '2026-08-08 20:28:14', type: 'WARNING', source: 'K8s.Watcher', message: 'Pod payments/payment-processor-79d8b8584f-x2k9l exited with OOMKilled (code 137)' },
    { time: '2026-08-08 20:28:15', type: 'INFO', source: 'Incident.Engine', message: 'Detected incident INC-0842: category=OOMKilled severity=CRITICAL' },
    { time: '2026-08-08 20:28:16', type: 'INFO', source: 'Outbox.Queue', message: 'Buffered incident INC-0842 in local disk Outbox queue (file-backed thread-safe)' },
    { time: '2026-08-08 20:28:17', type: 'SUCCESS', source: 'Cloud.SyncWorker', message: 'Synced payload INC-0842 to SkyOps Cloud API endpoint (201 Created)' },
    { time: '2026-08-08 20:25:01', type: 'WARNING', source: 'K8s.Watcher', message: 'Pod authentication/auth-gateway-6d7c4f4b9d-4m87q state: ErrImagePull' },
    { time: '2026-08-08 20:25:02', type: 'INFO', source: 'AI.Analyzer', message: 'Invoked Gemini flash diagnosis: manifest unknown for v3.0.0-rc1' },
    { time: '2026-08-08 20:20:00', type: 'INFO', source: 'Agent.Heartbeat', message: 'Agent telemetry heartbeat reported healthy connection to GKE control plane' },
  ];

  const filtered = sampleEvents.filter((e) => {
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
      {/* Simulation / Outbox Notice */}
      <div className="bg-amber-950/40 border border-amber-800/80 p-2.5 rounded flex items-center justify-between text-[11px] text-amber-200">
        <div className="flex items-center gap-2">
          <span className="px-1.5 py-0.5 rounded bg-amber-900 border border-amber-700 font-bold text-[10px] text-amber-300">
            SIMULATION / BUFFER STREAM
          </span>
          <span>Displaying reference event stream for outbox queue validation and agent watcher pipeline testing.</span>
        </div>
        <span className="text-amber-400 font-bold">Scope: {clusterId || 'ALL'}</span>
      </div>

      {/* Outbox Queue Telemetry Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 bg-neutral-900 border border-neutral-800 p-3 rounded">
        <div>
          <div className="text-[10px] text-neutral-500 uppercase">OUTBOX QUEUE STATUS</div>
          <div className="font-bold text-emerald-400 flex items-center gap-1.5 mt-0.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            ONLINE & SYNCED
          </div>
        </div>
        <div>
          <div className="text-[10px] text-neutral-500 uppercase">BUFFERED PAYLOADS</div>
          <div className="font-bold text-neutral-200 mt-0.5">0 Pending</div>
        </div>
        <div>
          <div className="text-[10px] text-neutral-500 uppercase">TOTAL SYNCED</div>
          <div className="font-bold text-cyan-400 mt-0.5">14,289 Items</div>
        </div>
        <div>
          <div className="text-[10px] text-neutral-500 uppercase">RETRY BACKOFF ENGINE</div>
          <div className="font-bold text-neutral-300 mt-0.5">Exponential (Max 30s)</div>
        </div>
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
          {filtered.map((evt, idx) => (
            <div key={idx} className="flex items-start gap-2 py-0.5 border-b border-neutral-900/60 hover:bg-neutral-900/40">
              <span className="text-neutral-500 shrink-0">{evt.time}</span>
              <span
                className={`px-1 rounded text-[10px] font-bold shrink-0 ${
                  evt.type === 'WARNING'
                    ? 'bg-amber-950 text-amber-400 border border-amber-800'
                    : evt.type === 'SUCCESS'
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                    : 'bg-blue-950 text-blue-400 border border-blue-800'
                }`}
              >
                {evt.type}
              </span>
              <span className="text-cyan-400 font-bold shrink-0">[{evt.source}]</span>
              <span className="text-neutral-300">{evt.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
