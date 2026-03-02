/**
 * Geo Experiment API Hooks
 *
 * Hooks for managing geo-lift experiments including power analysis and results.
 */

import { useState, useCallback, useEffect } from 'react'
import {
  graphqlRequest,
  QUERIES,
  MUTATIONS,
  GeoExperimentType,
  PowerAnalysisResultType,
  GeoExperimentResultType,
  CreateGeoExperimentInput,
  RunPowerAnalysisInput,
} from '@/lib/graphql'

// ============================================================================
// Types
// ============================================================================

interface GeoExperimentFilter {
  status?: string
  startDateFrom?: string
  startDateTo?: string
  primaryMetric?: string
}

interface UseGeoExperimentsOptions {
  autoFetch?: boolean
  filter?: GeoExperimentFilter
  limit?: number
  offset?: number
}

// ============================================================================
// Hooks
// ============================================================================

/**
 * Hook for fetching geo experiments
 */
export function useGeoExperiments(options: UseGeoExperimentsOptions = {}) {
  const { autoFetch = true, filter, limit = 50, offset = 0 } = options
  const [experiments, setExperiments] = useState<GeoExperimentType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchExperiments = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ geoExperiments: GeoExperimentType[] }>(
        QUERIES.GEO_EXPERIMENTS,
        { filter, limit, offset }
      )
      setExperiments(data.geoExperiments || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch geo experiments')
    } finally {
      setLoading(false)
    }
  }, [filter, limit, offset])

  useEffect(() => {
    if (autoFetch) {
      fetchExperiments()
    }
  }, [autoFetch, fetchExperiments])

  return { experiments, loading, error, refetch: fetchExperiments }
}

/**
 * Hook for fetching a single geo experiment
 */
export function useGeoExperiment(experimentId?: string) {
  const [experiment, setExperiment] = useState<GeoExperimentType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchExperiment = useCallback(async (id?: string) => {
    const targetId = id || experimentId
    if (!targetId) return null

    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ geoExperiment: GeoExperimentType }>(
        QUERIES.GEO_EXPERIMENT,
        { experimentId: targetId }
      )
      setExperiment(data.geoExperiment)
      return data.geoExperiment
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch geo experiment')
      return null
    } finally {
      setLoading(false)
    }
  }, [experimentId])

  useEffect(() => {
    if (experimentId) {
      fetchExperiment()
    }
  }, [experimentId, fetchExperiment])

  return { experiment, loading, error, refetch: fetchExperiment }
}

/**
 * Hook for creating geo experiments
 */
export function useCreateGeoExperiment() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const createExperiment = useCallback(async (input: CreateGeoExperimentInput): Promise<GeoExperimentType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ createGeoExperiment: GeoExperimentType }>(
        MUTATIONS.CREATE_GEO_EXPERIMENT,
        { input }
      )
      return data.createGeoExperiment
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to create geo experiment'
      setError(errorMsg)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { createExperiment, loading, error }
}

/**
 * Hook for running power analysis
 */
export function useRunPowerAnalysis() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<PowerAnalysisResultType | null>(null)

  const runPowerAnalysis = useCallback(async (input: RunPowerAnalysisInput): Promise<PowerAnalysisResultType | null> => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await graphqlRequest<{ runPowerAnalysis: PowerAnalysisResultType }>(
        MUTATIONS.RUN_POWER_ANALYSIS,
        { input }
      )
      setResult(data.runPowerAnalysis)
      return data.runPowerAnalysis
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to run power analysis'
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

  return { runPowerAnalysis, loading, error, result, reset }
}

/**
 * Hook for analyzing geo experiments
 */
export function useAnalyzeGeoExperiment() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<GeoExperimentResultType | null>(null)

  const analyzeExperiment = useCallback(async (experimentId: string): Promise<GeoExperimentResultType | null> => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await graphqlRequest<{ analyzeGeoExperiment: GeoExperimentResultType }>(
        MUTATIONS.ANALYZE_GEO_EXPERIMENT,
        { experimentId }
      )
      setResult(data.analyzeGeoExperiment)
      return data.analyzeGeoExperiment
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to analyze geo experiment'
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

  return { analyzeExperiment, loading, error, result, reset }
}

/**
 * Hook for managing geo experiment lifecycle
 */
export function useGeoExperimentActions() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const markReady = useCallback(async (experimentId: string): Promise<boolean> => {
    setLoading(true)
    setError(null)

    try {
      await graphqlRequest<{ markExperimentReady: GeoExperimentType }>(
        MUTATIONS.MARK_EXPERIMENT_READY,
        { experimentId }
      )
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to mark experiment ready')
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  const startExperiment = useCallback(async (experimentId: string): Promise<boolean> => {
    setLoading(true)
    setError(null)

    try {
      await graphqlRequest<{ startGeoExperiment: GeoExperimentType }>(
        MUTATIONS.START_GEO_EXPERIMENT,
        { experimentId }
      )
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start experiment')
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  const completeExperiment = useCallback(async (experimentId: string): Promise<boolean> => {
    setLoading(true)
    setError(null)

    try {
      await graphqlRequest<{ completeGeoExperiment: GeoExperimentType }>(
        MUTATIONS.COMPLETE_GEO_EXPERIMENT,
        { experimentId }
      )
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to complete experiment')
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  const archiveExperiment = useCallback(async (experimentId: string): Promise<boolean> => {
    setLoading(true)
    setError(null)

    try {
      await graphqlRequest<{ archiveGeoExperiment: GeoExperimentType }>(
        MUTATIONS.ARCHIVE_GEO_EXPERIMENT,
        { experimentId }
      )
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to archive experiment')
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  const deleteExperiment = useCallback(async (experimentId: string): Promise<boolean> => {
    setLoading(true)
    setError(null)

    try {
      await graphqlRequest<{ deleteGeoExperiment: boolean }>(
        MUTATIONS.DELETE_GEO_EXPERIMENT,
        { experimentId }
      )
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete experiment')
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    markReady,
    startExperiment,
    completeExperiment,
    archiveExperiment,
    deleteExperiment,
    loading,
    error,
  }
}

/**
 * Combined hook for all geo experiment mutations
 */
export function useGeoExperimentMutations() {
  const { createExperiment, loading: createLoading, error: createError } = useCreateGeoExperiment()
  const { runPowerAnalysis, loading: powerLoading, error: powerError, result: powerResult } = useRunPowerAnalysis()
  const { analyzeExperiment, loading: analyzeLoading, error: analyzeError, result: analyzeResult } = useAnalyzeGeoExperiment()
  const {
    markReady,
    startExperiment,
    completeExperiment,
    archiveExperiment,
    deleteExperiment,
    loading: actionLoading,
    error: actionError,
  } = useGeoExperimentActions()

  return {
    createExperiment,
    runPowerAnalysis,
    analyzeExperiment,
    markReady,
    startExperiment,
    completeExperiment,
    archiveExperiment,
    deleteExperiment,
    powerResult,
    analyzeResult,
    loading: createLoading || powerLoading || analyzeLoading || actionLoading,
    error: createError || powerError || analyzeError || actionError,
  }
}
