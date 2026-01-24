/**
 * Monitoring API Hooks
 */

import { useState, useCallback, useEffect } from 'react'
import {
  graphqlRequest,
  QUERIES,
  MUTATIONS,
  AlertType,
  MonitorConfigType,
  MonitoringSummaryType,
  MetricHistoryPoint,
  DriftCheckResult,
  PerformanceCheckResult,
} from '@/lib/graphql'

// ============================================================================
// useAlerts Hook
// ============================================================================

interface UseAlertsOptions {
  severity?: string
  acknowledged?: boolean
  limit?: number
  offset?: number
  autoFetch?: boolean
}

interface UseAlertsReturn {
  alerts: AlertType[]
  loading: boolean
  error: string | null
  fetchAlerts: (options?: UseAlertsOptions) => Promise<void>
  refetch: () => Promise<void>
}

interface AlertsResponse {
  alerts: AlertType[]
}

export function useAlerts(options: UseAlertsOptions = {}): UseAlertsReturn {
  const { severity, acknowledged, limit = 50, offset = 0, autoFetch = true } = options

  const [alerts, setAlerts] = useState<AlertType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchAlerts = useCallback(async (fetchOptions?: UseAlertsOptions) => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<AlertsResponse>(QUERIES.ALERTS, {
        severity: fetchOptions?.severity ?? severity ?? null,
        acknowledged: fetchOptions?.acknowledged ?? acknowledged ?? null,
        limit: fetchOptions?.limit ?? limit,
        offset: fetchOptions?.offset ?? offset,
      })
      setAlerts(data.alerts || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch alerts')
    } finally {
      setLoading(false)
    }
  }, [severity, acknowledged, limit, offset])

  const refetch = useCallback(async () => {
    await fetchAlerts()
  }, [fetchAlerts])

  useEffect(() => {
    if (autoFetch) {
      fetchAlerts()
    }
  }, [])

  return { alerts, loading, error, fetchAlerts, refetch }
}

// ============================================================================
// useActiveAlerts Hook
// ============================================================================

interface UseActiveAlertsReturn {
  alerts: AlertType[]
  loading: boolean
  error: string | null
  fetchActiveAlerts: (modelId?: string) => Promise<void>
  refetch: () => Promise<void>
}

interface ActiveAlertsResponse {
  activeAlerts: AlertType[]
}

export function useActiveAlerts(modelId?: string): UseActiveAlertsReturn {
  const [alerts, setAlerts] = useState<AlertType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchActiveAlerts = useCallback(async (id?: string) => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<ActiveAlertsResponse>(QUERIES.ACTIVE_ALERTS, {
        modelId: id ?? modelId ?? null,
      })
      setAlerts(data.activeAlerts || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch active alerts')
    } finally {
      setLoading(false)
    }
  }, [modelId])

  const refetch = useCallback(async () => {
    await fetchActiveAlerts()
  }, [fetchActiveAlerts])

  useEffect(() => {
    fetchActiveAlerts()
  }, [modelId])

  return { alerts, loading, error, fetchActiveAlerts, refetch }
}

// ============================================================================
// useMonitorConfigs Hook
// ============================================================================

interface UseMonitorConfigsOptions {
  modelId?: string
  isActive?: boolean
  autoFetch?: boolean
}

interface UseMonitorConfigsReturn {
  configs: MonitorConfigType[]
  loading: boolean
  error: string | null
  fetchConfigs: () => Promise<void>
  refetch: () => Promise<void>
}

interface MonitorConfigsResponse {
  monitorConfigs: MonitorConfigType[]
}

export function useMonitorConfigs(options: UseMonitorConfigsOptions = {}): UseMonitorConfigsReturn {
  const { modelId, isActive, autoFetch = true } = options

  const [configs, setConfigs] = useState<MonitorConfigType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchConfigs = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<MonitorConfigsResponse>(QUERIES.MONITOR_CONFIGS, {
        modelId: modelId ?? null,
        isActive: isActive ?? null,
      })
      setConfigs(data.monitorConfigs || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch monitor configs')
    } finally {
      setLoading(false)
    }
  }, [modelId, isActive])

  const refetch = useCallback(async () => {
    await fetchConfigs()
  }, [fetchConfigs])

  useEffect(() => {
    if (autoFetch) {
      fetchConfigs()
    }
  }, [])

  return { configs, loading, error, fetchConfigs, refetch }
}

// ============================================================================
// useMonitoringSummary Hook
// ============================================================================

interface UseMonitoringSummaryReturn {
  summary: MonitoringSummaryType | null
  loading: boolean
  error: string | null
  fetchSummary: (modelId?: string) => Promise<void>
  refetch: () => Promise<void>
}

interface MonitoringSummaryResponse {
  monitoringSummary: MonitoringSummaryType
}

export function useMonitoringSummary(modelId?: string): UseMonitoringSummaryReturn {
  const [summary, setSummary] = useState<MonitoringSummaryType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSummary = useCallback(async (id?: string) => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<MonitoringSummaryResponse>(QUERIES.MONITORING_SUMMARY, {
        modelId: id ?? modelId ?? null,
      })
      setSummary(data.monitoringSummary)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch monitoring summary')
    } finally {
      setLoading(false)
    }
  }, [modelId])

  const refetch = useCallback(async () => {
    await fetchSummary()
  }, [fetchSummary])

  useEffect(() => {
    fetchSummary()
  }, [modelId])

  return { summary, loading, error, fetchSummary, refetch }
}

// ============================================================================
// useMetricsHistory Hook
// ============================================================================

interface UseMetricsHistoryOptions {
  modelId: string
  metricName: string
  startDate?: string
  endDate?: string
}

interface UseMetricsHistoryReturn {
  history: MetricHistoryPoint[]
  loading: boolean
  error: string | null
  fetchHistory: () => Promise<void>
}

interface MetricsHistoryResponse {
  modelMetricsHistory: MetricHistoryPoint[]
}

export function useMetricsHistory(options: UseMetricsHistoryOptions): UseMetricsHistoryReturn {
  const { modelId, metricName, startDate, endDate } = options

  const [history, setHistory] = useState<MetricHistoryPoint[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchHistory = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<MetricsHistoryResponse>(QUERIES.MODEL_METRICS_HISTORY, {
        modelId,
        metricName,
        startDate: startDate ?? null,
        endDate: endDate ?? null,
      })
      setHistory(data.modelMetricsHistory || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics history')
    } finally {
      setLoading(false)
    }
  }, [modelId, metricName, startDate, endDate])

  useEffect(() => {
    if (modelId && metricName) {
      fetchHistory()
    }
  }, [modelId, metricName])

  return { history, loading, error, fetchHistory }
}

// ============================================================================
// Monitoring Mutation Hooks
// ============================================================================

interface UseAcknowledgeAlertReturn {
  acknowledge: (id: string, note?: string) => Promise<AlertType | null>
  loading: boolean
  error: string | null
}

export function useAcknowledgeAlert(): UseAcknowledgeAlertReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const acknowledge = useCallback(async (id: string, note?: string): Promise<AlertType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ acknowledgeAlert: AlertType }>(
        MUTATIONS.ACKNOWLEDGE_ALERT,
        { id, note: note ?? null }
      )
      return data.acknowledgeAlert
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to acknowledge alert')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { acknowledge, loading, error }
}

interface UseDismissAlertReturn {
  dismiss: (id: string) => Promise<boolean>
  loading: boolean
  error: string | null
}

export function useDismissAlert(): UseDismissAlertReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const dismiss = useCallback(async (id: string): Promise<boolean> => {
    setLoading(true)
    setError(null)

    try {
      await graphqlRequest<{ dismissAlert: boolean }>(MUTATIONS.DISMISS_ALERT, { id })
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to dismiss alert')
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  return { dismiss, loading, error }
}

interface UseCheckDriftReturn {
  checkDrift: (modelId: string) => Promise<DriftCheckResult | null>
  loading: boolean
  error: string | null
}

export function useCheckDrift(): UseCheckDriftReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const checkDrift = useCallback(async (modelId: string): Promise<DriftCheckResult | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ checkModelDrift: DriftCheckResult }>(
        MUTATIONS.CHECK_MODEL_DRIFT,
        { modelId }
      )
      return data.checkModelDrift
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check model drift')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { checkDrift, loading, error }
}

interface UseCheckPerformanceReturn {
  checkPerformance: (modelId: string) => Promise<PerformanceCheckResult | null>
  loading: boolean
  error: string | null
}

export function useCheckPerformance(): UseCheckPerformanceReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const checkPerformance = useCallback(async (modelId: string): Promise<PerformanceCheckResult | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ checkModelPerformance: PerformanceCheckResult }>(
        MUTATIONS.CHECK_MODEL_PERFORMANCE,
        { modelId }
      )
      return data.checkModelPerformance
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check model performance')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { checkPerformance, loading, error }
}

interface CreateMonitorConfigInput {
  modelId: string
  metricName: string
  alertType: string
  threshold: number
  windowSize?: number
  checkFrequency?: number
}

interface UseCreateMonitorConfigReturn {
  createConfig: (input: CreateMonitorConfigInput) => Promise<MonitorConfigType | null>
  loading: boolean
  error: string | null
}

export function useCreateMonitorConfig(): UseCreateMonitorConfigReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const createConfig = useCallback(async (input: CreateMonitorConfigInput): Promise<MonitorConfigType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ createMonitorConfig: MonitorConfigType }>(
        MUTATIONS.CREATE_MONITOR_CONFIG,
        { input }
      )
      return data.createMonitorConfig
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create monitor config')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { createConfig, loading, error }
}

interface UseDeleteMonitorConfigReturn {
  deleteConfig: (id: string) => Promise<boolean>
  loading: boolean
  error: string | null
}

export function useDeleteMonitorConfig(): UseDeleteMonitorConfigReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const deleteConfig = useCallback(async (id: string): Promise<boolean> => {
    setLoading(true)
    setError(null)

    try {
      await graphqlRequest<{ deleteMonitorConfig: boolean }>(MUTATIONS.DELETE_MONITOR_CONFIG, { id })
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete monitor config')
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  return { deleteConfig, loading, error }
}
