import React, { useEffect, useState } from 'react';
import { ClusterInfo, FilterOptions, Incident } from './types';
import { apiService } from './services/api';
import { Header } from './components/Header';
import { Navigation, TabType } from './components/Navigation';
import { IncidentsTable } from './components/IncidentsTable';
import { IncidentDetailView } from './components/IncidentDetailView';
import { ClusterOverview } from './components/ClusterOverview';
import { EventStreamConsole } from './components/EventStreamConsole';
import { SimulateIncidentModal } from './components/SimulateIncidentModal';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default function App() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [clusters, setClusters] = useState<ClusterInfo[]>([]);
  const [selectedClusterId, setSelectedClusterId] = useState<string>('ALL');
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('incidents');
  const [darkMode, setDarkMode] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isSimulateModalOpen, setIsSimulateModalOpen] = useState<boolean>(false);
  const [isApiUnavailable, setIsApiUnavailable] = useState<boolean>(false);
  const [apiErrorMessage, setApiErrorMessage] = useState<string>('');

  const [filters, setFilters] = useState<FilterOptions>({
    searchQuery: '',
    clusterId: 'ALL',
    severity: 'ALL',
    status: 'ALL',
    category: 'ALL',
    namespace: 'ALL',
  });

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
      console.error('SkyOps Cloud API error:', e);
      setIsApiUnavailable(true);
      setApiErrorMessage(e?.message || 'Could not establish connection to SkyOps Cloud Backend');
    } finally {
      if (!silent) setIsRefreshing(false);
    }
  };

  useEffect(() => {
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
  }, [selectedClusterId]);

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
          setSelectedIncident((prev) => prev ? { ...prev, status: 'RESOLVED', resolved_at: new Date().toISOString() } : null);
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
      } font-mono selection:bg-cyan-500/30 selection:text-cyan-200`}
    >
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
      />

      {/* Backend API Error Banner */}
      {isApiUnavailable && (
        <div className="bg-red-950/90 border-b border-red-800/80 px-4 py-2.5 flex items-center justify-between text-xs text-red-200 shadow-lg">
          <div className="flex items-center space-x-2.5">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 animate-pulse" />
            <span className="font-bold text-red-100 uppercase tracking-wider">
              SkyOps Cloud unavailable
            </span>
            <span className="text-red-300 border-l border-red-800/60 pl-2.5">
              {apiErrorMessage || 'Could not establish connection to live Cloud telemetry service'}
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

      {/* Navigation Sub-header (Shown when not in deep investigation detail view) */}
      {!selectedIncident && (
        <Navigation
          activeTab={activeTab}
          onTabChange={(tab) => setActiveTab(tab)}
          openIncidentCount={activeIncidentCount}
          totalClusterCount={clusters.length}
        />
      )}

      {/* Main Container */}
      <main className="mx-auto p-3 max-w-[1600px]">
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
            {activeTab === 'incidents' && (
              <IncidentsTable
                incidents={incidents}
                onSelectIncident={handleSelectIncident}
                filters={filters}
                onFilterChange={setFilters}
                onResolveIncident={handleResolveIncident}
              />
            )}

            {activeTab === 'infrastructure' && (
              <ClusterOverview
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

      {/* Simulation Trigger Modal */}
      <SimulateIncidentModal
        isOpen={isSimulateModalOpen}
        onClose={() => setIsSimulateModalOpen(false)}
        onInject={handleInjectScenario}
      />
    </div>
  );
}
