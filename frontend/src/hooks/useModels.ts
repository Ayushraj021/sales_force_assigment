/**
 * Model Management API Hooks
 */

import { useState, useCallback, useEffect } from 'react'
import { graphqlRequest, QUERIES, MUTATIONS, ModelType } from '@/lib/graphql'

interface UseModelsOptions {
  modelType?: string
  status?: string
  limit?: number
  offset?: number
  autoFetch?: boolean
}

interface CreateModelInput {
  name: string
  description?: string
  modelType: string
  datasetId: string
  config?: Record<string, unknown>
}

interface TrainingJobResult {
  modelId: string
  versionId: string
  status: string
  message: string
}

interface UseModelsReturn {
  models: ModelType[]
  loading: boolean
  error: string | null
  fetchModels: (options?: { modelType?: string; status?: string; limit?: number; offset?: number }) => Promise<void>
  refetch: () => Promise<void>
  createModel: (input: CreateModelInput) => Promise<ModelType>
  trainModel: (modelId: string) => Promise<TrainingJobResult>
  deleteModel: (id: string) => Promise<boolean>
}

interface ModelsResponse {
  models: ModelType[]
}

export function useModels(options: UseModelsOptions = {}): UseModelsReturn {
  const { modelType, status, limit = 50, offset = 0, autoFetch = true } = options

  const [models, setModels] = useState<ModelType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastParams, setLastParams] = useState({ modelType, status, limit, offset })

  const fetchModels = useCallback(async (fetchOptions?: { modelType?: string; status?: string; limit?: number; offset?: number }) => {
    const params = {
      modelType: fetchOptions?.modelType ?? lastParams.modelType,
      status: fetchOptions?.status ?? lastParams.status,
      limit: fetchOptions?.limit ?? lastParams.limit,
      offset: fetchOptions?.offset ?? lastParams.offset,
    }

    setLoading(true)
    setError(null)
    setLastParams(params)

    try {
      const data = await graphqlRequest<ModelsResponse>(
        QUERIES.MODELS,
        {
          modelType: params.modelType || null,
          status: params.status || null,
          limit: params.limit,
          offset: params.offset,
        }
      )
      setModels(data.models || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch models')
    } finally {
      setLoading(false)
    }
  }, [lastParams])

  const refetch = useCallback(async () => {
    await fetchModels()
  }, [fetchModels])

  const createModel = useCallback(async (input: CreateModelInput): Promise<ModelType> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ createModel: ModelType }>(
        MUTATIONS.CREATE_MODEL,
        { input }
      )
      // Refetch models to update the list
      await fetchModels()
      return data.createModel
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to create model'
      setError(errorMsg)
      throw new Error(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [fetchModels])

  const trainModel = useCallback(async (modelId: string): Promise<TrainingJobResult> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ trainModel: TrainingJobResult }>(
        MUTATIONS.TRAIN_MODEL,
        { modelId }
      )
      return data.trainModel
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to start training'
      setError(errorMsg)
      throw new Error(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [])

  const deleteModel = useCallback(async (id: string): Promise<boolean> => {
    setLoading(true)
    setError(null)

    try {
      await graphqlRequest<{ deleteModel: boolean }>(
        MUTATIONS.DELETE_MODEL,
        { id }
      )
      // Refetch models to update the list
      await fetchModels()
      return true
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to delete model'
      setError(errorMsg)
      throw new Error(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [fetchModels])

  useEffect(() => {
    if (autoFetch) {
      fetchModels({ modelType, status, limit, offset })
    }
  }, [])

  return { models, loading, error, fetchModels, refetch, createModel, trainModel, deleteModel }
}

interface UseModelReturn {
  model: ModelType | null
  loading: boolean
  error: string | null
  fetchModel: (id: string) => Promise<void>
  refetch: () => Promise<void>
}

interface ModelResponse {
  model: ModelType
}

export function useModel(modelId?: string): UseModelReturn {
  const [model, setModel] = useState<ModelType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastId, setLastId] = useState<string | undefined>(modelId)

  const fetchModel = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)
    setLastId(id)

    try {
      const data = await graphqlRequest<ModelResponse>(
        QUERIES.MODEL,
        { id }
      )
      setModel(data.model)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch model')
    } finally {
      setLoading(false)
    }
  }, [])

  const refetch = useCallback(async () => {
    if (lastId) {
      await fetchModel(lastId)
    }
  }, [fetchModel, lastId])

  useEffect(() => {
    if (modelId) {
      fetchModel(modelId)
    }
  }, [modelId, fetchModel])

  return { model, loading, error, fetchModel, refetch }
}
