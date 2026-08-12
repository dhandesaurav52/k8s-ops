import React from 'react';
import {
  AlertCircle,
  Cpu,
  LayoutDashboard,
  Radio,
  Server,
  Settings,
  Terminal,
  Activity,
  CheckCircle2,
  X,
  Menu,
  ShieldCheck,
  BarChart2,
  User,
  LogOut,
} from 'lucide-react';
import { NavTabType } from '../types';

interface SidebarProps {
  activeTab: NavTabType;
  onTabChange: (tab: NavTabType) => void;
  openIncidentCount: number;
  totalClusterCount: number;
  isCloudConnected: boolean;
  onOpenSettings: () => void;
  isMobileOpen: boolean;
  onToggleMobile: () => void;
  currentUser?: { username: string; role: string; email?: string } | null;
  onLogout?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onTabChange,
  openIncidentCount,
  totalClusterCount,
  isCloudConnected,
  onOpenSettings,
  isMobileOpen,
  onToggleMobile,
  currentUser,
  onLogout,
}) => {
  const navItems = [
    {
      id: 'overview' as NavTabType,
      label: 'Overview',
      icon: LayoutDashboard,
      badge: null,
      badgeColor: '',
    },
    {
      id: 'incidents' as NavTabType,
      label: 'Incidents',
      icon: AlertCircle,
      badge: openIncidentCount > 0 ? openIncidentCount : null,
      badgeColor: 'bg-amber-950/80 text-amber-400 border-amber-800/80',
    },
    {
      id: 'metrics' as NavTabType,
      label: 'Metrics',
      icon: BarChart2,
      badge: 'LIVE',
      badgeColor: 'bg-cyan-950/80 text-cyan-400 border-cyan-800/80',
    },
    {
      id: 'clusters' as NavTabType,
      label: 'Clusters',
      icon: Server,
      badge: totalClusterCount,
      badgeColor: 'bg-neutral-800 text-neutral-400 border-neutral-700',
    },
    {
      id: 'nodes' as NavTabType,
      label: 'Nodes',
      icon: Cpu,
      badge: null,
      badgeColor: '',
    },
    {
      id: 'events' as NavTabType,
      label: 'Event Stream',
      icon: Radio,
      badge: 'LIVE',
      badgeColor: 'bg-emerald-950/80 text-emerald-400 border-emerald-800/80',
    },
  ];

  return (
    <>
      {/* Mobile Drawer Backdrop */}
      {isMobileOpen && (
        <div
          onClick={onToggleMobile}
          className="fixed inset-0 bg-neutral-950/80 backdrop-blur-sm z-40 lg:hidden"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-neutral-950 border-r border-neutral-800/90 flex flex-col justify-between transition-transform duration-200 ease-in-out select-none font-mono ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div>
          {/* Brand Header */}
          <div className="p-4 border-b border-neutral-800/90 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded bg-cyan-950/60 border border-cyan-800/80 flex items-center justify-center text-cyan-400 shadow-inner shrink-0">
                <Terminal className="w-4 h-4 text-cyan-400" />
              </div>
              <div>
                <div className="flex items-center gap-1.5 font-bold tracking-tight text-neutral-100 text-sm">
                  SKYOPS
                  <span className="text-[10px] font-normal px-1.5 py-0.2 bg-cyan-950 text-cyan-400 border border-cyan-800/80 rounded">
                    v1.0.0
                  </span>
                </div>
                <div className="text-[10px] text-neutral-400 flex items-center gap-1 mt-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse inline-block" />
                  K8s Control Plane
                </div>
              </div>
            </div>

            <button
              onClick={onToggleMobile}
              className="lg:hidden p-1 text-neutral-400 hover:text-neutral-200"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <div className="p-3 space-y-1">
            <div className="px-2 py-1 text-[10px] text-neutral-500 uppercase tracking-wider font-semibold">
              CONSOLE
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    onTabChange(item.id);
                    if (isMobileOpen) onToggleMobile();
                  }}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded text-xs transition-colors cursor-pointer ${
                    isActive
                      ? 'bg-cyan-950/50 text-cyan-400 font-bold border border-cyan-800/60'
                      : 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900/60 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-neutral-500'}`} />
                    <span>{item.label}</span>
                  </div>

                  {item.badge !== null && (
                    <span
                      className={`px-1.5 py-0.2 text-[10px] rounded border font-mono ${item.badgeColor}`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* System Status Section at Bottom */}
        <div className="p-3 border-t border-neutral-800/90 space-y-3 bg-neutral-950/80">
          <div className="px-2 text-[10px] text-neutral-500 uppercase tracking-wider font-semibold">
            SYSTEM HEALTH
          </div>

          <div className="space-y-1.5 px-2 text-xs">
            {/* Cloud Status */}
            <div className="flex items-center justify-between">
              <span className="text-neutral-400 text-[11px]">Cloud API</span>
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-2 h-2 rounded-full ${
                    isCloudConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'
                  }`}
                />
                <span
                  className={`font-semibold text-[11px] ${
                    isCloudConnected ? 'text-emerald-400' : 'text-red-400'
                  }`}
                >
                  {isCloudConnected ? 'CONNECTED' : 'OFFLINE'}
                </span>
              </div>
            </div>

            {/* Agent Status */}
            <div className="flex items-center justify-between">
              <span className="text-neutral-400 text-[11px]">K8s Agent</span>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span className="font-semibold text-[11px] text-emerald-400">HEALTHY</span>
              </div>
            </div>
          </div>

          {/* Settings Trigger */}
          <button
            onClick={onOpenSettings}
            className="w-full flex items-center justify-between px-3 py-2 bg-neutral-900 hover:bg-neutral-800/80 border border-neutral-800 rounded text-neutral-300 hover:text-neutral-100 text-xs transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Settings className="w-3.5 h-3.5 text-neutral-400" />
              <span>System & API Info</span>
            </div>
            <span className="text-[10px] text-neutral-500">v1.0</span>
          </button>

          {/* User & Logout Badge */}
          {currentUser && (
            <div className="pt-2 border-t border-neutral-800/80 flex items-center justify-between px-1">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-7 h-7 rounded bg-cyan-950 border border-cyan-800/80 flex items-center justify-center text-cyan-400 shrink-0 text-xs font-bold">
                  {currentUser.username[0].toUpperCase()}
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-semibold text-neutral-200 truncate">
                    {currentUser.username}
                  </div>
                  <div className="text-[10px] text-cyan-400/80 font-mono capitalize">
                    {currentUser.role}
                  </div>
                </div>
              </div>

              {onLogout && (
                <button
                  onClick={onLogout}
                  className="p-1.5 text-neutral-400 hover:text-rose-400 hover:bg-rose-950/40 rounded border border-transparent hover:border-rose-800/50 transition"
                  title="Sign Out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              )}
            </div>
          )}
        </div>
      </aside>
    </>
  );
};
