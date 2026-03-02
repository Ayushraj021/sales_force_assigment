/**
 * Experiment API Hooks
 */

import { useState, useCallback, useEffect } from 'react'
import { graphqlRequest, QUERIES, ExperimentType } from '@/lib/graphql'

interface UseExperimentsOptions {
  status?: string
  limit?: number
  offset?: number
  autoFetch?: boolean
}

interface UseExperimentsReturn {
  experiments: ExperimentType[]
  loading: boolean
  error: string | null
  fetchExperiments: (options?: { status?: string; limit?: number; offset?: number }) => Promise<void>
  refetch: () => Promise<void>
}

interface ExperimentsResponse {
  experiments: ExperimentType[]
}

export function useExperiments(options: UseExperimentsOptions = {}): UseExperimentsReturn {
  const { status, limit = 50, offset = 0, autoFetch = true } = options

  const [experiments, setExperiments] = useState<ExperimentType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastParams, setLastParams] = useState({ status, limit, offset })

  const fetchExperiments = useCallback(async (fetchOptions?: { status?: string; limit?: number; offset?: number }) => {
    const params = {
      status: fetchOptions?.status ?? lastParams.status,
      limit: fetchOptions?.limit ?? lastParams.limit,
      offset: fetchOptions?.offset ?? lastParams.offset,
    }

    setLoading(true)
    setError(null)
    setLastParams(params)

    try {
      const data = await graphqlRequest<ExperimentsResponse>(
        QUERIES.EXPERIMENTS,
        {
          status: params.status || null,
          limit: params.limit,
          offset: params.offset,
        }
      )
      setExperiments(data.experiments || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch experiments')
    } finally {
      setLoading(false)
    }
  }, [lastParams])

  const refetch = useCallback(async () => {
    await fetchExperiments()
  }, [fetchExperiments])

  useEffect(() => {
    if (autoFetch) {
      fetchExperiments({ status, limit, offset })
    }
  }, [])

  return { experiments, loading, error, fetchExperiments, refetch }
}

interface UseExperimentReturn {
  experiment: ExperimentType | null
  loading: boolean
  error: string | null
  fetchExperiment: (id: string) => Promise<void>
  refetch: () => Promise<void>
}

interface ExperimentResponse {
  experiment: ExperimentType
}

export function useExperiment(experimentId?: string): UseExperimentReturn {
  const [experiment, setExperiment] = useState<ExperimentType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastId, setLastId] = useState<string | undefined>(experimentId)

  const fetchExperiment = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)
    setLastId(id)

    try {
      const data = await graphqlRequest<ExperimentResponse>(
        QUERIES.EXPERIMENT,
        { id }
      )
      setExperiment(data.experiment)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch experiment')
    } finally {
      setLoading(false)
    }
  }, [])

  const refetch = useCallback(async () => {
    if (lastId) {
      await fetchExperiment(lastId)
    }
  }, [fetchExperiment, lastId])

  useEffect(() => {
    if (experimentId) {
      fetchExperiment(experimentId)
    }
  }, [experimentId, fetchExperiment])

  return { experiment, loading, error, fetchExperiment, refetch }
}
