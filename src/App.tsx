import React, { useEffect, useState } from 'react';
import { ClusterInfo, FilterOptions, Incident, NavTabType } from './types';
import { apiService } from './services/api';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { OverviewDashboard } from './components/OverviewDashboard';
import { IncidentsTable } from './components/IncidentsTable';
import { IncidentDetailView } from './components/IncidentDetailView';
import { ClusterOverview } from './components/ClusterOverview';
import { NodesView } from './components/NodesView';
import { MetricsView } from './components/MetricsView';
import { EventStreamConsole } from './components/EventStreamConsole';
import { SettingsModal } from './components/SettingsModal';
import { SimulateIncidentModal } from './components/SimulateIncidentModal';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default function App() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [clusters, setClusters] = useState<ClusterInfo[]>([]);
  const [selectedClusterId, setSelectedClusterId] = useState<string>('ALL');
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [activeTab, setActiveTab] = useState<NavTabType>('overview');
  const [darkMode, setDarkMode] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isSimulateModalOpen, setIsSimulateModalOpen] = useState<boolean>(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState<boolean>(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState<boolean>(false);
  const [isApiUnavailable, setIsApiUnavailable] = useState<boolean>(false);
  const [apiErrorMessage, setApiErrorMessage] = useState<string>('');

  // Authentication & Setup state (Auth disabled)
  const [authStatus] = useState<{
    is_setup_completed: boolean;
    authenticated: boolean;
    user: { username: string; role: string; email?: string } | null;
  }>({
    is_setup_completed: true,
    authenticated: true,
    user: { username: 'admin', role: 'admin', email: 'admin@skyops.internal' },
  });
  const [isCheckingAuth, setIsCheckingAuth] = useState<boolean>(false);

  const [filters, setFilters] = useState<FilterOptions>({
    searchQuery: '',
    clusterId: 'ALL',
    severity: 'ALL',
    status: 'ALL',
    category: 'ALL',
    namespace: 'ALL',
  });

  // Auth bypass check
  const checkAuth = async () => {
    setIsCheckingAuth(false);
  };

  const handleLogout = async () => {
    // Auth system deprecated
  };

  useEffect(() => {
    checkAuth();
  }, []);

  // Load live data from SkyOps Cloud API
  const loadData = async (silent = false) => {
    if (!silent) setIsRefreshing(true);
    try {
      const clusterList = await apiService.fetchClusters();
      const incidentList = await apiService.fetchIncidents(selectedClusterId);

      setClusters(clusterList);
      setIncidents(incidentList);
      setIsApiUnavailable(false);
      setApiErrorMessage('');

      // Refresh currently selected incident detail if open
      if (selectedIncident) {
        const refreshed = await apiService.getIncident(
          selectedIncident.incident_id,
          selectedIncident.cluster_id
        );
        if (refreshed) setSelectedIncident(refreshed);
      }
    } catch (e: any) {
      console.warn('SkyOps Server API error:', e);
      // Only show top error banner if no cluster data is present or if user manually refreshed
      if (!silent || clusters.length === 0) {
        setIsApiUnavailable(true);
        setApiErrorMessage(e?.message || 'Could not establish connection to SkyOps Server');
      }
    } finally {
      if (!silent) setIsRefreshing(false);
    }
  };

  useEffect(() => {
    if (!authStatus?.authenticated) return;

    loadData();

    // Check URL hash for direct deep links e.g. #incidents/INC-0842
    const handleHashChange = async () => {
      const hash = window.location.hash;
      if (hash.startsWith('#incidents/')) {
        const incId = hash.replace('#incidents/', '');
        try {
          const inc = await apiService.getIncident(incId);
          if (inc) {
            setSelectedIncident(inc);
            setActiveTab('incidents');
          }
        } catch {
          // Ignore deep link fetch errors
        }
      }
    };

    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);

    // Live background polling every 5 seconds
    const interval = setInterval(() => {
      loadData(true);
    }, 5000);

    return () => {
      window.removeEventListener('hashchange', handleHashChange);
      clearInterval(interval);
    };
  }, [selectedClusterId, authStatus?.authenticated]);

  // Handle cluster selection
  const handleSelectCluster = (clusterId: string) => {
    setSelectedClusterId(clusterId);
    setFilters((prev) => ({ ...prev, clusterId }));
  };

  // Handle incident row select
  const handleSelectIncident = (incident: Incident) => {
    setSelectedIncident(incident);
    window.location.hash = `#incidents/${incident.incident_id}`;
  };

  // Handle back from detail view
  const handleBackToTable = () => {
    setSelectedIncident(null);
    window.location.hash = '';
  };

  // Handle incident resolution
  const handleResolveIncident = async (incidentId: string) => {
    try {
      const success = await apiService.resolveIncident(incidentId);
      if (success) {
        await loadData(true);
        if (selectedIncident && selectedIncident.incident_id === incidentId) {
          setSelectedIncident((prev) =>
            prev ? { ...prev, status: 'RESOLVED', resolved_at: new Date().toISOString() } : null
          );
        }
      }
    } catch (err: any) {
      console.error('Failed to resolve incident:', err);
      alert(`Error resolving incident: ${err.message || err}`);
    }
  };

  // Handle scenario simulation injection
  const handleInjectScenario = async (
    scenario: 'OOM' | 'IMAGE_PULL' | 'CRASH_LOOP' | 'PVC_PENDING'
  ) => {
    try {
      const newInc = await apiService.injectSimulationIncident(scenario);
      await loadData(true);
      setSelectedIncident(newInc);
      setActiveTab('incidents');
    } catch (err: any) {
      console.error('Failed to inject simulation:', err);
      alert(`Simulation failed: ${err.message || err}`);
    }
  };

  // Active counts
  const activeIncidentCount = incidents.filter((i) => i.status === 'OPEN').length;
  const criticalIncidentCount = incidents.filter(
    (i) => i.status === 'OPEN' && i.severity === 'CRITICAL'
  ).length;

  return (
    <div
      className={`min-h-screen ${
        darkMode ? 'bg-neutral-950 text-neutral-200' : 'bg-neutral-900 text-neutral-100'
      } font-mono selection:bg-cyan-500/30 selection:text-cyan-200 flex`}
    >
      {/* Left Navigation Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          setSelectedIncident(null);
          window.location.hash = '';
        }}
        openIncidentCount={activeIncidentCount}
        totalClusterCount={clusters.length}
        isCloudConnected={!isApiUnavailable}
        onOpenSettings={() => setIsSettingsModalOpen(true)}
        isMobileOpen={isMobileSidebarOpen}
        onToggleMobile={() => setIsMobileSidebarOpen(!isMobileSidebarOpen)}
        currentUser={authStatus?.user}
        onLogout={handleLogout}
      />

      {/* Main Content Workspace (Offset by Sidebar width on large screens) */}
      <div className="flex-1 lg:pl-64 flex flex-col min-w-0">
        {/* Top Header Bar */}
        <Header
          clusters={clusters}
          selectedClusterId={selectedClusterId}
          onSelectCluster={handleSelectCluster}
          activeIncidentCount={activeIncidentCount}
          criticalIncidentCount={criticalIncidentCount}
          searchQuery={filters.searchQuery}
          onSearchChange={(q) => setFilters({ ...filters, searchQuery: q })}
          darkMode={darkMode}
          onToggleDarkMode={() => setDarkMode(!darkMode)}
          isRefreshing={isRefreshing}
          onRefresh={() => loadData(false)}
          onOpenSimulateModal={() => setIsSimulateModalOpen(true)}
          onToggleMobileSidebar={() => setIsMobileSidebarOpen(!isMobileSidebarOpen)}
          isCloudConnected={!isApiUnavailable}
        />

        {/* Backend API Error Banner */}
        {isApiUnavailable && (
          <div className="bg-red-950/90 border-b border-red-800/80 px-4 py-2.5 flex items-center justify-between text-xs text-red-200 shadow-lg">
            <div className="flex items-center space-x-2.5">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 animate-pulse" />
              <span className="font-bold text-red-100 uppercase tracking-wider">
                SkyOps API unavailable
              </span>
              <span className="text-red-300 border-l border-red-800/60 pl-2.5">
                {apiErrorMessage || 'Could not establish connection to live SkyOps API service'}
              </span>
            </div>
            <button
              onClick={() => loadData(false)}
              disabled={isRefreshing}
              className="px-3 py-1 bg-red-900/90 hover:bg-red-800 border border-red-700/80 rounded text-red-100 font-mono text-xs flex items-center space-x-1.5 transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>Retry Connection</span>
            </button>
          </div>
        )}

        {/* Main Body Page View */}
        <main className="p-4 flex-1 overflow-x-hidden">
          {selectedIncident ? (
            /* FLAGSHIP INCIDENT INVESTIGATION CONSOLE */
            <IncidentDetailView
              incident={selectedIncident}
              onBack={handleBackToTable}
              onResolve={handleResolveIncident}
            />
          ) : (
            /* TABBED VIEWS */
            <>
              {activeTab === 'overview' && (
                <OverviewDashboard
                  clusters={clusters}
                  incidents={incidents}
                  selectedClusterId={selectedClusterId}
                  onSelectIncident={handleSelectIncident}
                  onNavigateTab={setActiveTab}
                  onSelectCluster={handleSelectCluster}
                />
              )}

              {activeTab === 'incidents' && (
                <IncidentsTable
                  incidents={incidents}
                  onSelectIncident={handleSelectIncident}
                  filters={filters}
                  onFilterChange={setFilters}
                  onResolveIncident={handleResolveIncident}
                />
              )}

              {activeTab === 'metrics' && (
                <MetricsView
                  selectedClusterId={selectedClusterId}
                  clusters={clusters}
                />
              )}

              {activeTab === 'clusters' && (
                <ClusterOverview
                  clusters={clusters}
                  selectedClusterId={selectedClusterId}
                  onSelectCluster={handleSelectCluster}
                  onNavigateTab={setActiveTab}
                />
              )}

              {activeTab === 'nodes' && (
                <NodesView
                  clusters={clusters}
                  selectedClusterId={selectedClusterId}
                  onSelectCluster={handleSelectCluster}
                />
              )}

              {activeTab === 'events' && (
                <EventStreamConsole clusterId={selectedClusterId} />
              )}
            </>
          )}
        </main>
      </div>

      {/* System Settings & API Modal */}
      <SettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
        isCloudConnected={!isApiUnavailable}
        clusters={clusters}
        incidents={incidents}
        onRefresh={() => loadData(false)}
      />

      {/* Simulation Trigger Modal */}
      <SimulateIncidentModal
        isOpen={isSimulateModalOpen}
        onClose={() => setIsSimulateModalOpen(false)}
        onInject={handleInjectScenario}
      />
    </div>
  );
}
