/**
 * ETL Pipeline API Hooks
 */

import { useState, useCallback, useEffect } from 'react'
import {
  graphqlRequest,
  QUERIES,
  MUTATIONS,
  EtlPipelineType,
  EtlPipelineRunType,
  EtlStepType,
} from '@/lib/graphql'

// ============================================================================
// usePipelines Hook
// ============================================================================

interface UsePipelinesOptions {
  status?: string
  limit?: number
  offset?: number
  autoFetch?: boolean
}

interface UsePipelinesReturn {
  pipelines: EtlPipelineType[]
  loading: boolean
  error: string | null
  fetchPipelines: (options?: UsePipelinesOptions) => Promise<void>
  refetch: () => Promise<void>
}

interface PipelinesResponse {
  etlPipelines: EtlPipelineType[]
}

export function usePipelines(options: UsePipelinesOptions = {}): UsePipelinesReturn {
  const { status, limit = 50, offset = 0, autoFetch = true } = options

  const [pipelines, setPipelines] = useState<EtlPipelineType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchPipelines = useCallback(async (fetchOptions?: UsePipelinesOptions) => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<PipelinesResponse>(QUERIES.ETL_PIPELINES, {
        status: fetchOptions?.status ?? status ?? null,
        limit: fetchOptions?.limit ?? limit,
        offset: fetchOptions?.offset ?? offset,
      })
      setPipelines(data.etlPipelines || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch pipelines')
    } finally {
      setLoading(false)
    }
  }, [status, limit, offset])

  const refetch = useCallback(async () => {
    await fetchPipelines()
  }, [fetchPipelines])

  useEffect(() => {
    if (autoFetch) {
      fetchPipelines()
    }
  }, [])

  return { pipelines, loading, error, fetchPipelines, refetch }
}

// ============================================================================
// usePipeline Hook
// ============================================================================

interface UsePipelineReturn {
  pipeline: EtlPipelineType | null
  loading: boolean
  error: string | null
  fetchPipeline: (id: string) => Promise<void>
  refetch: () => Promise<void>
}

interface PipelineResponse {
  etlPipeline: EtlPipelineType
}

export function usePipeline(pipelineId?: string): UsePipelineReturn {
  const [pipeline, setPipeline] = useState<EtlPipelineType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastId, setLastId] = useState<string | undefined>(pipelineId)

  const fetchPipeline = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)
    setLastId(id)

    try {
      const data = await graphqlRequest<PipelineResponse>(QUERIES.ETL_PIPELINE, { id })
      setPipeline(data.etlPipeline)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch pipeline')
    } finally {
      setLoading(false)
    }
  }, [])

  const refetch = useCallback(async () => {
    if (lastId) {
      await fetchPipeline(lastId)
    }
  }, [fetchPipeline, lastId])

  useEffect(() => {
    if (pipelineId) {
      fetchPipeline(pipelineId)
    }
  }, [pipelineId])

  return { pipeline, loading, error, fetchPipeline, refetch }
}

// ============================================================================
// usePipelineRuns Hook
// ============================================================================

interface UsePipelineRunsOptions {
  pipelineId: string
  status?: string
  limit?: number
  offset?: number
}

interface UsePipelineRunsReturn {
  runs: EtlPipelineRunType[]
  loading: boolean
  error: string | null
  fetchRuns: () => Promise<void>
  refetch: () => Promise<void>
}

interface PipelineRunsResponse {
  etlPipelineRuns: EtlPipelineRunType[]
}

export function usePipelineRuns(options: UsePipelineRunsOptions): UsePipelineRunsReturn {
  const { pipelineId, status, limit = 20, offset = 0 } = options

  const [runs, setRuns] = useState<EtlPipelineRunType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchRuns = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<PipelineRunsResponse>(QUERIES.ETL_PIPELINE_RUNS, {
        pipelineId,
        status: status ?? null,
        limit,
        offset,
      })
      setRuns(data.etlPipelineRuns || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch pipeline runs')
    } finally {
      setLoading(false)
    }
  }, [pipelineId, status, limit, offset])

  const refetch = useCallback(async () => {
    await fetchRuns()
  }, [fetchRuns])

  useEffect(() => {
    if (pipelineId) {
      fetchRuns()
    }
  }, [pipelineId])

  return { runs, loading, error, fetchRuns, refetch }
}

// ============================================================================
// ETL Mutation Hooks
// ============================================================================

interface CreatePipelineInput {
  name: string
  description?: string
  schedule?: string
  config?: Record<string, unknown>
}

interface UseCreatePipelineReturn {
  createPipeline: (input: CreatePipelineInput) => Promise<EtlPipelineType | null>
  loading: boolean
  error: string | null
}

export function useCreatePipeline(): UseCreatePipelineReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const createPipeline = useCallback(async (input: CreatePipelineInput): Promise<EtlPipelineType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ createEtlPipeline: EtlPipelineType }>(
        MUTATIONS.CREATE_ETL_PIPELINE,
        { input }
      )
      return data.createEtlPipeline
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create pipeline')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { createPipeline, loading, error }
}

interface UpdatePipelineInput {
  name?: string
  description?: string
  schedule?: string
  status?: string
  config?: Record<string, unknown>
}

interface UseUpdatePipelineReturn {
  updatePipeline: (id: string, input: UpdatePipelineInput) => Promise<EtlPipelineType | null>
  loading: boolean
  error: string | null
}

export function useUpdatePipeline(): UseUpdatePipelineReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updatePipeline = useCallback(async (id: string, input: UpdatePipelineInput): Promise<EtlPipelineType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ updateEtlPipeline: EtlPipelineType }>(
        MUTATIONS.UPDATE_ETL_PIPELINE,
        { id, input }
      )
      return data.updateEtlPipeline
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update pipeline')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { updatePipeline, loading, error }
}

interface UseDeletePipelineReturn {
  deletePipeline: (id: string) => Promise<boolean>
  loading: boolean
  error: string | null
}

export function useDeletePipeline(): UseDeletePipelineReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const deletePipeline = useCallback(async (id: string): Promise<boolean> => {
    setLoading(true)
    setError(null)

    try {
      await graphqlRequest<{ deleteEtlPipeline: boolean }>(MUTATIONS.DELETE_ETL_PIPELINE, { id })
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete pipeline')
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  return { deletePipeline, loading, error }
}

interface CreateStepInput {
  name: string
  stepType: 'extract' | 'transform' | 'load' | 'validate'
  stepOrder: number
  config?: Record<string, unknown>
}

interface UseAddStepReturn {
  addStep: (pipelineId: string, input: CreateStepInput) => Promise<EtlStepType | null>
  loading: boolean
  error: string | null
}

export function useAddStep(): UseAddStepReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const addStep = useCallback(async (pipelineId: string, input: CreateStepInput): Promise<EtlStepType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ addEtlStep: EtlStepType }>(
        MUTATIONS.ADD_ETL_STEP,
        { pipelineId, input }
      )
      return data.addEtlStep
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add step')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { addStep, loading, error }
}

interface UseRunPipelineReturn {
  runPipeline: (pipelineId: string, config?: Record<string, unknown>) => Promise<EtlPipelineRunType | null>
  loading: boolean
  error: string | null
}

export function useRunPipeline(): UseRunPipelineReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runPipeline = useCallback(async (pipelineId: string, config?: Record<string, unknown>): Promise<EtlPipelineRunType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ runEtlPipeline: EtlPipelineRunType }>(
        MUTATIONS.RUN_ETL_PIPELINE,
        { pipelineId, config: config ?? null }
      )
      return data.runEtlPipeline
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run pipeline')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { runPipeline, loading, error }
}

interface UseCancelRunReturn {
  cancelRun: (runId: string) => Promise<EtlPipelineRunType | null>
  loading: boolean
  error: string | null
}

export function useCancelRun(): UseCancelRunReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const cancelRun = useCallback(async (runId: string): Promise<EtlPipelineRunType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ cancelEtlRun: EtlPipelineRunType }>(
        MUTATIONS.CANCEL_ETL_RUN,
        { runId }
      )
      return data.cancelEtlRun
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel run')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { cancelRun, loading, error }
}

interface UseRetryRunReturn {
  retryRun: (runId: string, fromStep?: string) => Promise<EtlPipelineRunType | null>
  loading: boolean
  error: string | null
}

export function useRetryRun(): UseRetryRunReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const retryRun = useCallback(async (runId: string, fromStep?: string): Promise<EtlPipelineRunType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ retryEtlRun: EtlPipelineRunType }>(
        MUTATIONS.RETRY_ETL_RUN,
        { runId, fromStep: fromStep ?? null }
      )
      return data.retryEtlRun
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry run')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { retryRun, loading, error }
}
