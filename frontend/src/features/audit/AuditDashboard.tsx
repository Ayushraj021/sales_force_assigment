/**
 * Audit Dashboard Component
 *
 * View and search audit logs for compliance and security.
 */

import { useState, useMemo } from "react";
import { motion } from "framer-motion";

interface AuditLog {
  id: string;
  timestamp: string;
  userId: string;
  userName: string;
  action: string;
  resource: string;
  resourceId?: string;
  details?: Record<string, unknown>;
  ipAddress?: string;
  userAgent?: string;
  status: "success" | "failure" | "warning";
}

interface AuditFilters {
  userId?: string;
  action?: string;
  resource?: string;
  status?: string;
  startDate?: string;
  endDate?: string;
}

interface AuditDashboardProps {
  logs?: AuditLog[];
  users?: Array<{ id: string; name: string }>;
  isLoading?: boolean;
  onFilterChange?: (filters: AuditFilters) => void;
  onExport?: (format: "csv" | "json") => Promise<void>;
}

const mockLogs: AuditLog[] = [
  {
    id: "log-1",
    timestamp: "2024-01-24T10:30:00Z",
    userId: "user-1",
    userName: "John Doe",
    action: "CREATE",
    resource: "forecast",
    resourceId: "forecast-123",
    details: { model: "mmm", channels: 5 },
    ipAddress: "192.168.1.100",
    status: "success",
  },
  {
    id: "log-2",
    timestamp: "2024-01-24T10:25:00Z",
    userId: "user-2",
    userName: "Jane Smith",
    action: "UPDATE",
    resource: "dataset",
    resourceId: "dataset-456",
    details: { rows_added: 1500 },
    ipAddress: "192.168.1.101",
    status: "success",
  },
  {
    id: "log-3",
    timestamp: "2024-01-24T10:20:00Z",
    userId: "user-1",
    userName: "John Doe",
    action: "DELETE",
    resource: "report",
    resourceId: "report-789",
    ipAddress: "192.168.1.100",
    status: "success",
  },
  {
    id: "log-4",
    timestamp: "2024-01-24T10:15:00Z",
    userId: "user-3",
    userName: "Bob Wilson",
    action: "LOGIN",
    resource: "auth",
    ipAddress: "192.168.1.102",
    status: "failure",
    details: { reason: "Invalid password" },
  },
  {
    id: "log-5",
    timestamp: "2024-01-24T10:10:00Z",
    userId: "user-2",
    userName: "Jane Smith",
    action: "EXPORT",
    resource: "data",
    resourceId: "export-321",
    details: { format: "csv", rows: 5000 },
    ipAddress: "192.168.1.101",
    status: "success",
  },
];

const actions = ["CREATE", "READ", "UPDATE", "DELETE", "LOGIN", "LOGOUT", "EXPORT", "SHARE"];
const resources = ["forecast", "dataset", "report", "model", "auth", "data", "settings"];

export function AuditDashboard({
  logs = mockLogs,
  users = [
    { id: "user-1", name: "John Doe" },
    { id: "user-2", name: "Jane Smith" },
    { id: "user-3", name: "Bob Wilson" },
  ],
  isLoading = false,
  onFilterChange,
  onExport,
}: AuditDashboardProps) {
  const [filters, setFilters] = useState<AuditFilters>({});
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const updateFilter = (key: keyof AuditFilters, value: string) => {
    const newFilters = { ...filters, [key]: value || undefined };
    setFilters(newFilters);
    onFilterChange?.(newFilters);
  };

  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      if (filters.userId && log.userId !== filters.userId) return false;
      if (filters.action && log.action !== filters.action) return false;
      if (filters.resource && log.resource !== filters.resource) return false;
      if (filters.status && log.status !== filters.status) return false;
      if (filters.startDate && log.timestamp < filters.startDate) return false;
      if (filters.endDate && log.timestamp > filters.endDate) return false;
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        return (
          log.userName.toLowerCase().includes(query) ||
          log.action.toLowerCase().includes(query) ||
          log.resource.toLowerCase().includes(query) ||
          (log.resourceId?.toLowerCase().includes(query) ?? false)
        );
      }
      return true;
    });
  }, [logs, filters, searchQuery]);

  const stats = useMemo(() => {
    const total = filteredLogs.length;
    const success = filteredLogs.filter((l) => l.status === "success").length;
    const failure = filteredLogs.filter((l) => l.status === "failure").length;
    const uniqueUsers = new Set(filteredLogs.map((l) => l.userId)).size;
    return { total, success, failure, uniqueUsers };
  }, [filteredLogs]);

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "success":
        return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
      case "failure":
        return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
      case "warning":
        return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400";
      default:
        return "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300";
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case "CREATE":
        return "text-green-600";
      case "DELETE":
        return "text-red-600";
      case "UPDATE":
        return "text-blue-600";
      case "LOGIN":
      case "LOGOUT":
        return "text-purple-600";
      case "EXPORT":
        return "text-orange-600";
      default:
        return "text-gray-600";
    }
  };

  const handleExport = async (format: "csv" | "json") => {
    if (onExport) {
      await onExport(format);
    } else {
      // Mock export
      const data = format === "json" ? JSON.stringify(filteredLogs, null, 2) : "CSV data";
      const blob = new Blob([data], { type: format === "json" ? "application/json" : "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit-logs.${format}`;
      a.click();
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Audit Logs
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Track and review all system activities for compliance and security
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">Total Events</div>
          <div className="text-2xl font-bold mt-1">{stats.total}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">Successful</div>
          <div className="text-2xl font-bold mt-1 text-green-600">{stats.success}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">Failed</div>
          <div className="text-2xl font-bold mt-1 text-red-600">{stats.failure}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">Unique Users</div>
          <div className="text-2xl font-bold mt-1">{stats.uniqueUsers}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700 mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium mb-1">Search</label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search logs..."
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">User</label>
            <select
              value={filters.userId || ""}
              onChange={(e) => updateFilter("userId", e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
            >
              <option value="">All Users</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Action</label>
            <select
              value={filters.action || ""}
              onChange={(e) => updateFilter("action", e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
            >
              <option value="">All Actions</option>
              {actions.map((action) => (
                <option key={action} value={action}>
                  {action}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Resource</label>
            <select
              value={filters.resource || ""}
              onChange={(e) => updateFilter("resource", e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
            >
              <option value="">All Resources</option>
              {resources.map((resource) => (
                <option key={resource} value={resource}>
                  {resource}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Status</label>
            <select
              value={filters.status || ""}
              onChange={(e) => updateFilter("status", e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800"
            >
              <option value="">All Status</option>
              <option value="success">Success</option>
              <option value="failure">Failure</option>
              <option value="warning">Warning</option>
            </select>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handleExport("csv")}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Export CSV
            </button>
            <button
              onClick={() => handleExport("json")}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Export JSON
            </button>
          </div>
        </div>
      </div>

      {/* Logs Table */}
      {isLoading ? (
        <div className="h-96 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Timestamp</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">User</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Action</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Resource</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">IP Address</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {filteredLogs.map((log) => (
                  <motion.tr
                    key={log.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer"
                    onClick={() => setSelectedLog(log)}
                  >
                    <td className="px-4 py-3 text-sm font-mono">
                      {formatTimestamp(log.timestamp)}
                    </td>
                    <td className="px-4 py-3 text-sm">{log.userName}</td>
                    <td className={`px-4 py-3 text-sm font-medium ${getActionColor(log.action)}`}>
                      {log.action}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span>{log.resource}</span>
                      {log.resourceId && (
                        <span className="text-gray-400 ml-1 text-xs">
                          ({log.resourceId})
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${getStatusColor(log.status)}`}
                      >
                        {log.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm font-mono text-gray-500">
                      {log.ipAddress || "-"}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {log.details ? (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedLog(log);
                          }}
                          className="text-primary hover:underline"
                        >
                          View Details
                        </button>
                      ) : (
                        "-"
                      )}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>

          {filteredLogs.length === 0 && (
            <div className="py-12 text-center text-gray-500">
              No audit logs found matching your criteria
            </div>
          )}
        </div>
      )}

      {/* Detail Modal */}
      {selectedLog && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedLog(null)}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-lg w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">Audit Log Details</h2>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-gray-500 hover:text-gray-700"
              >
                Close
              </button>
            </div>

            <dl className="space-y-3">
              <div>
                <dt className="text-sm text-gray-500">Timestamp</dt>
                <dd className="font-mono">{formatTimestamp(selectedLog.timestamp)}</dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">User</dt>
                <dd>{selectedLog.userName} ({selectedLog.userId})</dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">Action</dt>
                <dd className={`font-medium ${getActionColor(selectedLog.action)}`}>
                  {selectedLog.action}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">Resource</dt>
                <dd>
                  {selectedLog.resource}
                  {selectedLog.resourceId && ` (${selectedLog.resourceId})`}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">Status</dt>
                <dd>
                  <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(selectedLog.status)}`}>
                    {selectedLog.status}
                  </span>
                </dd>
              </div>
              {selectedLog.ipAddress && (
                <div>
                  <dt className="text-sm text-gray-500">IP Address</dt>
                  <dd className="font-mono">{selectedLog.ipAddress}</dd>
                </div>
              )}
              {selectedLog.userAgent && (
                <div>
                  <dt className="text-sm text-gray-500">User Agent</dt>
                  <dd className="text-sm break-all">{selectedLog.userAgent}</dd>
                </div>
              )}
              {selectedLog.details && (
                <div>
                  <dt className="text-sm text-gray-500">Details</dt>
                  <dd>
                    <pre className="mt-1 p-2 bg-gray-100 dark:bg-gray-700 rounded text-xs overflow-auto">
                      {JSON.stringify(selectedLog.details, null, 2)}
                    </pre>
                  </dd>
                </div>
              )}
            </dl>
          </motion.div>
        </motion.div>
      )}
    </div>
  );
}

export default AuditDashboard;
