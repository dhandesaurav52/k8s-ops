import React, { useState } from 'react';
import {
  AlertTriangle,
  ArrowUpDown,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Filter,
  Layers,
  RotateCcw,
  ShieldAlert,
  Clock,
} from 'lucide-react';
import { FilterOptions, Incident } from '../types';
import { SeverityBadge, StatusBadge } from './IncidentStatusBadge';

interface IncidentsTableProps {
  incidents: Incident[];
  onSelectIncident: (incident: Incident) => void;
  filters: FilterOptions;
  onFilterChange: (filters: FilterOptions) => void;
  onResolveIncident: (incidentId: string) => void;
}

type SortField = 'last_seen' | 'severity' | 'incident_id' | 'resource_name' | 'category';

export const IncidentsTable: React.FC<IncidentsTableProps> = ({
  incidents,
  onSelectIncident,
  filters,
  onFilterChange,
  onResolveIncident,
}) => {
  const [sortField, setSortField] = useState<SortField>('last_seen');
  const [sortAsc, setSortAsc] = useState<boolean>(false);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Extract unique namespaces and categories for filter dropdowns
  const namespaces = Array.from(
    new Set(incidents.map((i) => i.resource?.namespace || 'default'))
  ).sort();
  const categories = Array.from(new Set(incidents.map((i) => i.category))).sort();

  // Calculate high density stats
  const activeCount = incidents.filter((i) => i.status === 'OPEN').length;
  const criticalCount = incidents.filter((i) => i.status === 'OPEN' && i.severity === 'CRITICAL').length;
  const highCount = incidents.filter((i) => i.status === 'OPEN' && i.severity === 'HIGH').length;
  const mediumCount = incidents.filter((i) => i.status === 'OPEN' && i.severity === 'MEDIUM').length;
  const lowCount = incidents.filter((i) => i.status === 'OPEN' && i.severity === 'LOW').length;
  const resolvedCount = incidents.filter((i) => i.status === 'RESOLVED').length;

  // Apply search and filter rules
  const filteredIncidents = incidents.filter((inc) => {
    if (filters.status !== 'ALL' && inc.status !== filters.status) return false;
    if (filters.severity !== 'ALL' && inc.severity !== filters.severity) return false;
    if (filters.namespace && filters.namespace !== 'ALL' && inc.resource?.namespace !== filters.namespace)
      return false;
    if (filters.category && filters.category !== 'ALL' && inc.category !== filters.category)
      return false;
    if (filters.clusterId && filters.clusterId !== 'ALL' && inc.cluster_id !== filters.clusterId)
      return false;

    if (filters.searchQuery) {
      const q = filters.searchQuery.toLowerCase();
      const matchId = inc.incident_id.toLowerCase().includes(q);
      const matchRes = inc.resource?.name?.toLowerCase().includes(q);
      const matchNs = inc.resource?.namespace?.toLowerCase().includes(q);
      const matchCat = inc.category.toLowerCase().includes(q);
      const matchState = inc.current_state.toLowerCase().includes(q);
      const matchCluster = inc.cluster_id.toLowerCase().includes(q);
      if (!matchId && !matchRes && !matchNs && !matchCat && !matchState && !matchCluster)
        return false;
    }
    return true;
  });

  // Sorting
  const sortedIncidents = [...filteredIncidents].sort((a, b) => {
    let comparison = 0;
    if (sortField === 'last_seen') {
      comparison = new Date(b.last_seen).getTime() - new Date(a.last_seen).getTime();
    } else if (sortField === 'severity') {
      const rank = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };
      comparison = (rank[b.severity] || 0) - (rank[a.severity] || 0);
    } else if (sortField === 'incident_id') {
      comparison = a.incident_id.localeCompare(b.incident_id);
    } else if (sortField === 'resource_name') {
      comparison = (a.resource?.name || '').localeCompare(b.resource?.name || '');
    } else if (sortField === 'category') {
      comparison = a.category.localeCompare(b.category);
    }

    return sortAsc ? -comparison : comparison;
  });

  // Pagination calculations
  const totalPages = Math.ceil(sortedIncidents.length / pageSize) || 1;
  const validCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (validCurrentPage - 1) * pageSize;
  const paginatedIncidents = sortedIncidents.slice(startIndex, startIndex + pageSize);

  const handleSortToggle = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const formatRelativeTime = (isoString: string) => {
    try {
      const diffMs = Date.now() - new Date(isoString).getTime();
      const mins = Math.floor(diffMs / (1000 * 60));
      if (mins < 1) return 'just now';
      if (mins < 60) return `${mins}m ago`;
      const hours = Math.floor(mins / 60);
      if (hours < 24) return `${hours}h ago`;
      return `${Math.floor(hours / 24)}d ago`;
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-3 font-mono text-xs text-neutral-200">
      {/* Dense Operational Summary Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 bg-neutral-900 border border-neutral-800 p-2.5 rounded shadow">
        <div className="border-r border-neutral-800/80 pr-2">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider">ACTIVE INCIDENTS</div>
          <div className="text-lg font-bold text-neutral-100 flex items-center gap-1.5 mt-0.5">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            {activeCount}
          </div>
        </div>

        <div className="border-r border-neutral-800/80 pr-2">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider">CRITICAL</div>
          <div className="text-lg font-bold text-red-400 flex items-center gap-1.5 mt-0.5">
            <ShieldAlert className="w-4 h-4 text-red-400" />
            {criticalCount}
          </div>
        </div>

        <div className="border-r border-neutral-800/80 pr-2">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider">HIGH</div>
          <div className="text-lg font-bold text-orange-400 mt-0.5">{highCount}</div>
        </div>

        <div className="border-r border-neutral-800/80 pr-2">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider">MEDIUM / LOW</div>
          <div className="text-lg font-bold text-yellow-400 mt-0.5">
            {mediumCount} <span className="text-neutral-500 text-xs font-normal">/ {lowCount}</span>
          </div>
        </div>

        <div className="border-r border-neutral-800/80 pr-2">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider">RESOLVED</div>
          <div className="text-lg font-bold text-emerald-400 flex items-center gap-1.5 mt-0.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            {resolvedCount}
          </div>
        </div>

        <div>
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider">TOTAL TRACKED</div>
          <div className="text-lg font-bold text-neutral-300 mt-0.5">{incidents.length}</div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 bg-neutral-900 border border-neutral-800 p-2 rounded">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1 text-neutral-400 text-[11px] font-medium mr-1">
            <Filter className="w-3.5 h-3.5 text-neutral-500" />
            <span>FILTERS:</span>
          </div>

          {/* Status Filter */}
          <select
            value={filters.status}
            onChange={(e) => onFilterChange({ ...filters, status: e.target.value as any })}
            className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-xs text-neutral-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">Status: ALL</option>
            <option value="OPEN">Status: OPEN</option>
            <option value="RESOLVED">Status: RESOLVED</option>
          </select>

          {/* Severity Filter */}
          <select
            value={filters.severity}
            onChange={(e) => onFilterChange({ ...filters, severity: e.target.value as any })}
            className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-xs text-neutral-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">Severity: ALL</option>
            <option value="CRITICAL">Severity: CRITICAL</option>
            <option value="HIGH">Severity: HIGH</option>
            <option value="MEDIUM">Severity: MEDIUM</option>
            <option value="LOW">Severity: LOW</option>
          </select>

          {/* Namespace Filter */}
          <select
            value={filters.namespace}
            onChange={(e) => onFilterChange({ ...filters, namespace: e.target.value })}
            className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-xs text-neutral-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">Namespace: ALL</option>
            {namespaces.map((ns) => (
              <option key={ns} value={ns}>
                ns/{ns}
              </option>
            ))}
          </select>

          {/* Category Filter */}
          <select
            value={filters.category}
            onChange={(e) => onFilterChange({ ...filters, category: e.target.value })}
            className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-xs text-neutral-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">Category: ALL</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>

        {/* Clear Filters Button */}
        {(filters.status !== 'ALL' ||
          filters.severity !== 'ALL' ||
          filters.namespace !== 'ALL' ||
          filters.category !== 'ALL' ||
          filters.searchQuery) && (
          <button
            onClick={() =>
              onFilterChange({
                searchQuery: '',
                clusterId: filters.clusterId,
                severity: 'ALL',
                status: 'ALL',
                category: 'ALL',
                namespace: 'ALL',
              })
            }
            className="flex items-center gap-1 text-[11px] text-cyan-400 hover:text-cyan-300 font-medium px-2 py-0.5 rounded border border-cyan-800/60 bg-cyan-950/40 cursor-pointer"
          >
            <RotateCcw className="w-3 h-3" />
            RESET FILTERS
          </button>
        )}
      </div>

      {/* Main Dense Table */}
      <div className="border border-neutral-800 rounded bg-neutral-950 overflow-x-auto shadow-xl">
        <table className="w-full text-left border-collapse font-mono text-xs">
          <thead>
            <tr className="border-b border-neutral-800 bg-neutral-900/90 text-neutral-400 select-none uppercase text-[10px] tracking-wider">
              <th className="py-2.5 px-3 font-semibold w-24">
                <button
                  onClick={() => handleSortToggle('incident_id')}
                  className="flex items-center gap-1 hover:text-neutral-200 cursor-pointer"
                >
                  ID <ArrowUpDown className="w-3 h-3 text-neutral-600" />
                </button>
              </th>
              <th className="py-2.5 px-3 font-semibold w-24">
                <button
                  onClick={() => handleSortToggle('severity')}
                  className="flex items-center gap-1 hover:text-neutral-200 cursor-pointer"
                >
                  SEVERITY <ArrowUpDown className="w-3 h-3 text-neutral-600" />
                </button>
              </th>
              <th className="py-2.5 px-3 font-semibold w-20">STATUS</th>
              <th className="py-2.5 px-3 font-semibold">
                <button
                  onClick={() => handleSortToggle('resource_name')}
                  className="flex items-center gap-1 hover:text-neutral-200 cursor-pointer"
                >
                  TARGET RESOURCE <ArrowUpDown className="w-3 h-3 text-neutral-600" />
                </button>
              </th>
              <th className="py-2.5 px-3 font-semibold w-36">
                <button
                  onClick={() => handleSortToggle('category')}
                  className="flex items-center gap-1 hover:text-neutral-200 cursor-pointer"
                >
                  CATEGORY <ArrowUpDown className="w-3 h-3 text-neutral-600" />
                </button>
              </th>
              <th className="py-2.5 px-3 font-semibold min-w-[200px]">CURRENT STATE</th>
              <th className="py-2.5 px-3 font-semibold text-center w-16">SEEN</th>
              <th className="py-2.5 px-3 font-semibold text-right w-28">
                <button
                  onClick={() => handleSortToggle('last_seen')}
                  className="flex items-center gap-1 hover:text-neutral-200 justify-end w-full cursor-pointer"
                >
                  LAST SEEN <ArrowUpDown className="w-3 h-3 text-neutral-600" />
                </button>
              </th>
              <th className="py-2.5 px-3 font-semibold text-center w-20">ACTION</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-800/80">
            {paginatedIncidents.length === 0 ? (
              <tr>
                <td colSpan={9} className="py-8 text-center text-neutral-500 font-mono">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <Layers className="w-8 h-8 text-neutral-700" />
                    <span>No incidents match the active filters or cluster scope.</span>
                  </div>
                </td>
              </tr>
            ) : (
              paginatedIncidents.map((inc) => {
                const isResolved = inc.status === 'RESOLVED';
                return (
                  <tr
                    key={inc.incident_id}
                    onClick={() => onSelectIncident(inc)}
                    className="hover:bg-neutral-900/80 cursor-pointer transition-colors group"
                  >
                    {/* ID */}
                    <td className="py-2.5 px-3 font-bold text-neutral-200 whitespace-nowrap">
                      <div className="flex items-center gap-1">
                        <span className="text-cyan-400 group-hover:underline">{inc.incident_id}</span>
                      </div>
                      <div className="text-[10px] text-neutral-500 truncate font-mono max-w-[90px]">
                        {inc.cluster_id.replace('skyops-cluster-', '')}
                      </div>
                    </td>

                    {/* Severity */}
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <SeverityBadge severity={inc.severity} />
                    </td>

                    {/* Status */}
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <StatusBadge status={inc.status} />
                    </td>

                    {/* Target Resource */}
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-neutral-100 flex items-center gap-1.5 truncate max-w-[220px]">
                        <span className="px-1 py-0.2 rounded bg-neutral-900 border border-neutral-800 text-[10px] text-neutral-400 uppercase font-mono">
                          {inc.resource?.kind || 'Pod'}
                        </span>
                        <span className="truncate">{inc.resource?.name}</span>
                      </div>
                      <div className="text-[10px] text-neutral-400 font-mono">
                        ns/<span className="text-neutral-300">{inc.resource?.namespace || 'default'}</span>
                      </div>
                    </td>

                    {/* Category */}
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <span className="px-1.5 py-0.5 rounded bg-neutral-900 border border-neutral-800 text-neutral-300 font-mono font-medium">
                        {inc.category}
                      </span>
                    </td>

                    {/* Current State */}
                    <td className="py-2.5 px-3 text-neutral-300 font-mono max-w-xs truncate">
                      <span className="text-neutral-200">{inc.current_state}</span>
                    </td>

                    {/* Occurrences */}
                    <td className="py-2.5 px-3 text-center whitespace-nowrap font-bold text-neutral-300">
                      <span className="px-2 py-0.5 bg-neutral-900 border border-neutral-800 rounded">
                        {inc.occurrences}x
                      </span>
                    </td>

                    {/* Last Seen */}
                    <td className="py-2.5 px-3 text-right whitespace-nowrap text-neutral-400 font-mono">
                      <div className="flex items-center justify-end gap-1 text-neutral-300">
                        <Clock className="w-3 h-3 text-neutral-500" />
                        {formatRelativeTime(inc.last_seen)}
                      </div>
                      <div className="text-[10px] text-neutral-500">
                        {new Date(inc.last_seen).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </td>

                    {/* Action */}
                    <td className="py-2.5 px-3 text-center whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                      {!isResolved ? (
                        <button
                          onClick={() => onResolveIncident(inc.incident_id)}
                          className="px-2 py-1 bg-emerald-950 text-emerald-400 hover:bg-emerald-900 border border-emerald-800 rounded text-[10px] font-mono font-medium transition-colors cursor-pointer"
                          title="Mark incident resolved"
                        >
                          RESOLVE
                        </button>
                      ) : (
                        <div className="text-neutral-600 flex justify-center">
                          <ChevronRight className="w-4 h-4 text-neutral-600 group-hover:text-cyan-400" />
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

        {/* Table Footer / Pagination Controls */}
        <div className="p-2.5 bg-neutral-900 border-t border-neutral-800 flex items-center justify-between text-xs text-neutral-400">
          <div>
            Showing <strong className="text-neutral-200">{paginatedIncidents.length}</strong> of{' '}
            <strong className="text-neutral-200">{sortedIncidents.length}</strong> filtered incidents
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span>Per page:</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="bg-neutral-950 border border-neutral-800 rounded px-1.5 py-0.5 text-xs text-neutral-200"
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
              </select>
            </div>

            <div className="flex items-center gap-1">
              <button
                disabled={validCurrentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="p-1 rounded bg-neutral-950 border border-neutral-800 text-neutral-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-neutral-800"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-2 text-neutral-300 font-bold">
                {validCurrentPage} / {totalPages}
              </span>
              <button
                disabled={validCurrentPage >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                className="p-1 rounded bg-neutral-950 border border-neutral-800 text-neutral-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-neutral-800"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
