import React from 'react';
import { AlertCircle, AlertTriangle, Cpu, HardDrive, PlusCircle, X } from 'lucide-react';

interface SimulateIncidentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onInject: (scenario: 'OOM' | 'IMAGE_PULL' | 'CRASH_LOOP' | 'PVC_PENDING') => void;
}

export const SimulateIncidentModal: React.FC<SimulateIncidentModalProps> = ({
  isOpen,
  onClose,
  onInject,
}) => {
  if (!isOpen) return null;

  const scenarios = [
    {
      id: 'OOM' as const,
      title: 'OOMKilled Signal (Exit Code 137)',
      severity: 'CRITICAL',
      color: 'border-red-800 bg-red-950/40 text-red-400',
      description: 'Simulate memory limit breach on payment-api worker pod resulting in cgroup kernel SIGKILL.',
      icon: Cpu,
    },
    {
      id: 'IMAGE_PULL' as const,
      title: 'ErrImagePull / ImagePullBackOff',
      severity: 'HIGH',
      color: 'border-orange-800 bg-orange-950/40 text-orange-400',
      description: 'Simulate invalid container image tag v4.0.1-nightly manifest unknown error in catalog namespace.',
      icon: AlertTriangle,
    },
    {
      id: 'PVC_PENDING' as const,
      title: 'PVC Volume Mount Failure',
      severity: 'HIGH',
      color: 'border-amber-800 bg-amber-950/40 text-amber-400',
      description: 'Simulate StorageClass persistent disk quota exceeded error blocking postgres-db pod schedule.',
      icon: HardDrive,
    },
    {
      id: 'CRASH_LOOP' as const,
      title: 'CrashLoopBackOff (Config Error)',
      severity: 'MEDIUM',
      color: 'border-yellow-800 bg-yellow-950/40 text-yellow-400',
      description: 'Simulate data exporter job failing on database handshake connection error.',
      icon: AlertCircle,
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 font-mono text-xs select-none">
      <div className="bg-neutral-900 border border-neutral-800 rounded-lg max-w-lg w-full p-4 shadow-2xl space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-neutral-800">
          <div className="flex items-center gap-2 font-bold text-neutral-100 text-sm">
            <PlusCircle className="w-4 h-4 text-cyan-400" />
            <span>INJECT KUBERNETES SIGNAL SIMULATION</span>
          </div>
          <button onClick={onClose} className="p-1 text-neutral-400 hover:text-neutral-100">
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-neutral-400 text-xs">
          Select a real-world Kubernetes failure mode to inject into the SkyOps incident detection and AI reasoning engine:
        </p>

        <div className="space-y-2">
          {scenarios.map((sc) => {
            const Icon = sc.icon;
            return (
              <button
                key={sc.id}
                onClick={() => {
                  onInject(sc.id);
                  onClose();
                }}
                className={`w-full text-left p-3 rounded border ${sc.color} hover:brightness-125 transition-all flex items-start gap-3 group`}
              >
                <Icon className="w-5 h-5 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-neutral-100 text-xs group-hover:text-cyan-300">
                      {sc.title}
                    </span>
                    <span className="text-[10px] uppercase font-bold px-1.5 py-0.2 rounded border border-current">
                      {sc.severity}
                    </span>
                  </div>
                  <p className="text-[11px] text-neutral-300">{sc.description}</p>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
