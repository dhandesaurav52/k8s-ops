import React from 'react';
import { AlertCircle, Cpu, FileText, Radio, Layers } from 'lucide-react';

export type TabType = 'incidents' | 'infrastructure' | 'events';

interface NavigationProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  openIncidentCount: number;
  totalClusterCount: number;
}

export const Navigation: React.FC<NavigationProps> = ({
  activeTab,
  onTabChange,
  openIncidentCount,
  totalClusterCount,
}) => {
  const navItems = [
    {
      id: 'incidents' as TabType,
      label: 'INCIDENTS',
      icon: AlertCircle,
      badge: openIncidentCount > 0 ? openIncidentCount : null,
      badgeColor: 'bg-amber-950 text-amber-400 border-amber-800',
    },
    {
      id: 'infrastructure' as TabType,
      label: 'CLUSTERS & NODES',
      icon: Cpu,
      badge: totalClusterCount,
      badgeColor: 'bg-neutral-800 text-neutral-400 border-neutral-700',
    },
    {
      id: 'events' as TabType,
      label: 'EVENT STREAM & OUTBOX',
      icon: Radio,
      badge: 'LIVE',
      badgeColor: 'bg-emerald-950 text-emerald-400 border-emerald-800',
    },
  ];

  return (
    <nav className="border-b border-neutral-800 bg-neutral-950/90 backdrop-blur select-none">
      <div className="mx-auto px-3 flex items-center gap-1 font-mono text-xs">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`flex items-center gap-2 px-3 py-2 border-b-2 font-medium transition-colors ${
                isActive
                  ? 'border-cyan-500 text-cyan-400 bg-neutral-900/60'
                  : 'border-transparent text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900/30'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-cyan-400' : 'text-neutral-500'}`} />
              <span>{item.label}</span>
              {item.badge !== null && (
                <span
                  className={`ml-1 px-1.5 py-0.2 text-[10px] rounded border font-mono ${item.badgeColor}`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
};
