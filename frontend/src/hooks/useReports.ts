/**
 * Reports API Hooks
 *
 * Hooks for fetching and managing reports, scheduled reports, and exports.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  graphqlRequest,
  QUERIES,
  MUTATIONS,
  ReportTemplateType,
  ScheduledReportItemType,
  ExportItemType,
  GenerateReportResultType,
} from '@/lib/graphql'

// ============================================================================
// Types
// ============================================================================

export interface ScheduleReportInput {
  reportId: string
  name: string
  scheduleType: 'daily' | 'weekly' | 'monthly'
  scheduleConfig?: Record<string, unknown>
  timezone?: string
  deliveryMethod?: string
  deliveryConfig?: Record<string, unknown>
  recipients: string[]
  exportFormat?: string
}

export interface CreateReportInput {
  name: string
  description?: string
  reportType: string
  template?: Record<string, unknown>
  sections?: string[]
  availableFormats?: string[]
}

export interface GenerateReportInput {
  reportId: string
  exportFormat?: string
  parameters?: Record<string, unknown>
}

// ============================================================================
// Hooks
// ============================================================================

interface UseReportsOptions {
  autoFetch?: boolean
  reportType?: string
  limit?: number
  offset?: number
}

/**
 * Hook for fetching report templates
 */
export function useReports(options: UseReportsOptions = {}) {
  const { autoFetch = true, reportType, limit = 50, offset = 0 } = options
  const [reports, setReports] = useState<ReportTemplateType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchReports = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ reports: ReportTemplateType[] }>(
        QUERIES.REPORTS,
        { reportType, limit, offset }
      )
      setReports(data.reports)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch reports')
    } finally {
      setLoading(false)
    }
  }, [reportType, limit, offset])

  useEffect(() => {
    if (autoFetch) {
      fetchReports()
    }
  }, [autoFetch, fetchReports])

  return { reports, loading, error, refetch: fetchReports }
}

interface UseScheduledReportsOptions {
  autoFetch?: boolean
  isActive?: boolean
  limit?: number
  offset?: number
}

/**
 * Hook for fetching scheduled reports
 */
export function useScheduledReports(options: UseScheduledReportsOptions = {}) {
  const { autoFetch = true, isActive, limit = 50, offset = 0 } = options
  const [scheduledReports, setScheduledReports] = useState<ScheduledReportItemType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchScheduledReports = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ scheduledReports: ScheduledReportItemType[] }>(
        QUERIES.SCHEDULED_REPORTS,
        { isActive, limit, offset }
      )
      setScheduledReports(data.scheduledReports)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch scheduled reports')
    } finally {
      setLoading(false)
    }
  }, [isActive, limit, offset])

  useEffect(() => {
    if (autoFetch) {
      fetchScheduledReports()
    }
  }, [autoFetch, fetchScheduledReports])

  return { scheduledReports, loading, error, refetch: fetchScheduledReports }
}

interface UseExportOptions {
  autoFetch?: boolean
  pollInterval?: number // ms, 0 to disable polling
}

/**
 * Hook for fetching export status with optional polling
 */
export function useExport(exportId?: string, options: UseExportOptions = {}) {
  const { autoFetch = true, pollInterval = 2000 } = options
  const [exportData, setExportData] = useState<ExportItemType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  const fetchExport = useCallback(async (id?: string) => {
    const targetId = id || exportId
    if (!targetId) return null

    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ export: ExportItemType }>(
        QUERIES.EXPORT,
        { id: targetId }
      )
      setExportData(data.export)
      return data.export
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch export')
      return null
    } finally {
      setLoading(false)
    }
  }, [exportId])

  // Set up polling when export is pending/processing
  useEffect(() => {
    if (!autoFetch || !exportId) return

    fetchExport()

    // Clear any existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }

    // Only poll if export is in progress
    if (pollInterval > 0 && exportData && ['pending', 'processing'].includes(exportData.status)) {
      intervalRef.current = setInterval(() => {
        fetchExport()
      }, pollInterval)
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [autoFetch, exportId, pollInterval, exportData?.status, fetchExport])

  // Stop polling when export completes
  useEffect(() => {
    if (exportData && ['completed', 'failed'].includes(exportData.status)) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [exportData?.status])

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  return { export: exportData, loading, error, fetchExport, stopPolling }
}

/**
 * Hook for generating reports
 */
export function useGenerateReport() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<GenerateReportResultType | null>(null)

  const generateReport = useCallback(async (input: GenerateReportInput): Promise<GenerateReportResultType | null> => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await graphqlRequest<{ generateReport: GenerateReportResultType }>(
        MUTATIONS.GENERATE_REPORT,
        { input }
      )
      setResult(data.generateReport)
      return data.generateReport
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to generate report'
      setError(errorMsg)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setError(null)
    setResult(null)
  }, [])

  return { generateReport, loading, error, result, reset }
}

/**
 * Hook for scheduling reports
 */
export function useScheduleReport() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const scheduleReport = useCallback(async (input: ScheduleReportInput): Promise<ScheduledReportItemType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ scheduleReport: ScheduledReportItemType }>(
        MUTATIONS.SCHEDULE_REPORT,
        { input }
      )
      return data.scheduleReport
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to schedule report'
      setError(errorMsg)
      throw new Error(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [])

  return { scheduleReport, loading, error }
}

/**
 * Hook for creating reports
 */
export function useCreateReport() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const createReport = useCallback(async (input: CreateReportInput): Promise<ReportTemplateType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ createReport: ReportTemplateType }>(
        MUTATIONS.CREATE_REPORT,
        { input }
      )
      return data.createReport
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to create report'
      setError(errorMsg)
      throw new Error(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [])

  return { createReport, loading, error }
}

/**
 * Hook for canceling scheduled reports
 */
export function useCancelScheduledReport() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const cancelScheduledReport = useCallback(async (scheduledId: string): Promise<boolean> => {
    setLoading(true)
    setError(null)

    try {
      await graphqlRequest<{ cancelScheduledReport: boolean }>(
        MUTATIONS.CANCEL_SCHEDULED_REPORT,
        { id: scheduledId }
      )
      return true
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to cancel scheduled report'
      setError(errorMsg)
      throw new Error(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [])

  return { cancelScheduledReport, loading, error }
}

/**
 * Combined hook for report mutations
 */
export function useReportMutations() {
  const { createReport, loading: createLoading, error: createError } = useCreateReport()
  const { generateReport, loading: generateLoading, error: generateError, result, reset } = useGenerateReport()
  const { scheduleReport, loading: scheduleLoading, error: scheduleError } = useScheduleReport()
  const { cancelScheduledReport, loading: cancelLoading, error: cancelError } = useCancelScheduledReport()

  return {
    createReport,
    generateReport,
    scheduleReport,
    cancelScheduledReport,
    result,
    reset,
    loading: createLoading || generateLoading || scheduleLoading || cancelLoading,
    error: createError || generateError || scheduleError || cancelError,
  }
}
