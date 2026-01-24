import { useState, useEffect } from 'react'
import {
  BellAlertIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  FunnelIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import {
  useAlerts,
  useMonitoringSummary,
  useMonitorConfigs,
  useAcknowledgeAlert,
  useDismissAlert,
} from '@/hooks/useMonitoring'

export function MonitoringDashboard() {
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all')

  // API hooks
  const { alerts, loading: alertsLoading, error: alertsError, refetch: refetchAlerts } = useAlerts()
  const { summary, loading: summaryLoading, refetch: refetchSummary } = useMonitoringSummary()
  const { configs, loading: configsLoading, refetch: refetchConfigs } = useMonitorConfigs()
  const { acknowledge, loading: acknowledgeLoading } = useAcknowledgeAlert()
  const { dismiss, loading: dismissLoading } = useDismissAlert()

  const loading = alertsLoading || summaryLoading || configsLoading

  // Map API alerts to local format
  const mappedAlerts = alerts.map(alert => ({
    id: alert.id,
    alertType: alert.alertType as 'drift' | 'performance' | 'latency' | 'error_rate' | 'threshold',
    severity: alert.severity,
    modelName: alert.modelId || 'Unknown Model',
    message: alert.message,
    metricName: alert.metricName,
    currentValue: alert.currentValue,
    thresholdValue: alert.threshold,
    timestamp: alert.createdAt,
    acknowledged: alert.isAcknowledged,
  }))

  const handleRefresh = async () => {
    await Promise.all([refetchAlerts(), refetchSummary(), refetchConfigs()])
    toast.success('Monitoring data refreshed')
  }

  const handleAcknowledge = async (alertId: string) => {
    const result = await acknowledge(alertId)
    if (result) {
      toast.success('Alert acknowledged')
      refetchAlerts()
    }
  }

  const handleDismiss = async (alertId: string) => {
    const result = await dismiss(alertId)
    if (result) {
      toast.success('Alert dismissed')
      refetchAlerts()
    }
  }

  const getSeverityIcon = (severity: 'info' | 'warning' | 'critical') => {
    switch (severity) {
      case 'info':
        return <CheckCircleIcon className="h-5 w-5 text-blue-500" />
      case 'warning':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
      case 'critical':
        return <XCircleIcon className="h-5 w-5 text-red-500" />
    }
  }

  const getSeverityBadge = (severity: 'info' | 'warning' | 'critical') => {
    const colors = {
      info: 'bg-blue-100 text-blue-800',
      warning: 'bg-yellow-100 text-yellow-800',
      critical: 'bg-red-100 text-red-800',
    }
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[severity]}`}>
        {severity.charAt(0).toUpperCase() + severity.slice(1)}
      </span>
    )
  }

  const filteredAlerts = mappedAlerts.filter(
    a => selectedSeverity === 'all' || a.severity === selectedSeverity
  )

  const criticalCount = summary?.criticalAlerts ?? mappedAlerts.filter(a => a.severity === 'critical' && !a.acknowledged).length
  const warningCount = summary?.warningAlerts ?? mappedAlerts.filter(a => a.severity === 'warning' && !a.acknowledged).length

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Model Monitoring</h1>
          <p className="mt-1 text-sm text-gray-600">
            Monitor model performance, drift detection, and alerts.
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="btn btn-outline"
          >
            <ArrowPathIcon className={`h-5 w-5 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {alertsError && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          Error loading alerts: {alertsError}
        </div>
      )}

      {/* Alert Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <BellAlertIcon className="h-8 w-8 text-gray-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500">Total Alerts</p>
              <p className="text-2xl font-bold text-gray-900">{summary?.totalAlerts ?? mappedAlerts.length}</p>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4 border-l-4 border-red-500">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <XCircleIcon className="h-8 w-8 text-red-500" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500">Critical</p>
              <p className="text-2xl font-bold text-red-600">{criticalCount}</p>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4 border-l-4 border-yellow-500">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <ExclamationTriangleIcon className="h-8 w-8 text-yellow-500" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500">Warnings</p>
              <p className="text-2xl font-bold text-yellow-600">{warningCount}</p>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <ChartBarIcon className="h-8 w-8 text-gray-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500">Active Monitors</p>
              <p className="text-2xl font-bold text-gray-900">{summary?.activeMonitors ?? configs.length}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Alerts Panel */}
        <div className="lg:col-span-2 bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
            <h2 className="text-lg font-medium text-gray-900 flex items-center">
              <BellAlertIcon className="h-5 w-5 text-gray-400 mr-2" />
              Active Alerts
            </h2>
            <div className="flex items-center space-x-2">
              <FunnelIcon className="h-5 w-5 text-gray-400" />
              <select
                value={selectedSeverity}
                onChange={(e) => setSelectedSeverity(e.target.value)}
                className="text-sm border-gray-300 rounded-md"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="warning">Warning</option>
                <option value="info">Info</option>
              </select>
            </div>
          </div>
          <ul className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
            {alertsLoading ? (
              <li className="px-6 py-8 text-center text-gray-500">
                Loading alerts...
              </li>
            ) : filteredAlerts.length === 0 ? (
              <li className="px-6 py-8 text-center text-gray-500">
                No alerts to display
              </li>
            ) : (
              filteredAlerts.map((alert) => (
                <li key={alert.id} className={`px-6 py-4 ${alert.acknowledged ? 'bg-gray-50' : ''}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex items-start">
                      {getSeverityIcon(alert.severity)}
                      <div className="ml-3">
                        <div className="flex items-center space-x-2">
                          <p className="text-sm font-medium text-gray-900">{alert.modelName}</p>
                          {getSeverityBadge(alert.severity)}
                          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                            {alert.alertType}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">{alert.message}</p>
                        {alert.currentValue !== undefined && (
                          <p className="text-xs text-gray-500 mt-1">
                            Current: {alert.currentValue.toFixed(2)} | Threshold: {alert.thresholdValue?.toFixed(2)}
                          </p>
                        )}
                        <p className="text-xs text-gray-400 mt-1">
                          {new Date(alert.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {!alert.acknowledged && (
                        <button
                          onClick={() => handleAcknowledge(alert.id)}
                          disabled={acknowledgeLoading}
                          className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
                        >
                          Acknowledge
                        </button>
                      )}
                      <button
                        onClick={() => handleDismiss(alert.id)}
                        disabled={dismissLoading}
                        className="text-sm text-gray-400 hover:text-gray-600 disabled:opacity-50"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                </li>
              ))
            )}
          </ul>
        </div>

        {/* Summary Panel */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900 flex items-center">
              <ChartBarIcon className="h-5 w-5 text-gray-400 mr-2" />
              Monitoring Summary
            </h2>
          </div>
          <div className="p-6">
            {summaryLoading ? (
              <p className="text-center text-gray-500">Loading summary...</p>
            ) : summary ? (
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-500">Total Alerts</span>
                  <span className="font-medium">{summary.totalAlerts}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Critical</span>
                  <span className="font-medium text-red-600">{summary.criticalAlerts}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Warnings</span>
                  <span className="font-medium text-yellow-600">{summary.warningAlerts}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Info</span>
                  <span className="font-medium text-blue-600">{summary.infoAlerts}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Acknowledged</span>
                  <span className="font-medium text-gray-600">{summary.acknowledgedAlerts}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Active Monitors</span>
                  <span className="font-medium">{summary.activeMonitors}</span>
                </div>
                {summary.lastCheckTime && (
                  <div className="pt-2 border-t text-xs text-gray-400">
                    Last check: {new Date(summary.lastCheckTime).toLocaleString()}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-center text-gray-500">No summary data available</p>
            )}
          </div>
        </div>
      </div>

      {/* Monitor Configurations */}
      <div className="bg-white shadow rounded-lg mt-6">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-lg font-medium text-gray-900 flex items-center">
            <Cog6ToothIcon className="h-5 w-5 text-gray-400 mr-2" />
            Monitor Configurations
          </h2>
          <button className="btn btn-primary btn-sm">
            Add Configuration
          </button>
        </div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Model ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Metric
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Threshold
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Check Frequency
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {configsLoading ? (
              <tr>
                <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                  Loading configurations...
                </td>
              </tr>
            ) : configs.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                  No configurations found
                </td>
              </tr>
            ) : (
              configs.map((config) => (
                <tr key={config.id}>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">
                    {config.modelId.slice(0, 8)}...
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {config.metricName}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {config.threshold}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {config.checkFrequency} sec
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      config.isActive ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {config.isActive ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <button className="text-blue-600 hover:text-blue-800 mr-3">
                      Edit
                    </button>
                    <button className="text-red-600 hover:text-red-800">
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
