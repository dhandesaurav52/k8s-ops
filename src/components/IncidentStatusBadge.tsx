import React from 'react';
import { IncidentStatus, SeverityLevel } from '../types';

interface SeverityBadgeProps {
  severity: SeverityLevel;
  className?: string;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity, className = '' }) => {
  let colorClasses = '';
  switch (severity) {
    case 'CRITICAL':
      colorClasses = 'bg-red-950/80 text-red-400 border-red-800/80';
      break;
    case 'HIGH':
      colorClasses = 'bg-orange-950/80 text-orange-400 border-orange-800/80';
      break;
    case 'MEDIUM':
      colorClasses = 'bg-yellow-950/80 text-yellow-400 border-yellow-800/80';
      break;
    case 'LOW':
      colorClasses = 'bg-blue-950/80 text-blue-400 border-blue-800/80';
      break;
    default:
      colorClasses = 'bg-neutral-900 text-neutral-400 border-neutral-700';
  }

  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-mono font-medium border tracking-wide uppercase ${colorClasses} ${className}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
          severity === 'CRITICAL'
            ? 'bg-red-500 animate-pulse'
            : severity === 'HIGH'
            ? 'bg-orange-500'
            : severity === 'MEDIUM'
            ? 'bg-yellow-500'
            : 'bg-blue-500'
        }`}
      />
      {severity}
    </span>
  );
};

interface StatusBadgeProps {
  status: IncidentStatus;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  const isResolved = status === 'RESOLVED';
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-mono font-medium border uppercase tracking-wider ${
        isResolved
          ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/80'
          : 'bg-amber-950/60 text-amber-400 border-amber-800/80'
      } ${className}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
          isResolved ? 'bg-emerald-500' : 'bg-amber-500 animate-ping'
        }`}
      />
      {status}
    </span>
  );
};
