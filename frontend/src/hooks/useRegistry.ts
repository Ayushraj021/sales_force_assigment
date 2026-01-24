/**
 * Model Registry API Hooks
 */

import { useState, useCallback, useEffect } from 'react'
import {
  graphqlRequest,
  QUERIES,
  MUTATIONS,
  RegisteredModelType,
  RegistryModelVersionType,
  ModelVersionComparisonType,
} from '@/lib/graphql'

// ============================================================================
// useRegisteredModels Hook
// ============================================================================

interface UseRegisteredModelsOptions {
  stage?: string
  limit?: number
  offset?: number
  autoFetch?: boolean
}

interface UseRegisteredModelsReturn {
  models: RegisteredModelType[]
  loading: boolean
  error: string | null
  fetchModels: (options?: UseRegisteredModelsOptions) => Promise<void>
  refetch: () => Promise<void>
}

interface RegisteredModelsResponse {
  registeredModels: RegisteredModelType[]
}

export function useRegisteredModels(options: UseRegisteredModelsOptions = {}): UseRegisteredModelsReturn {
  const { stage, limit = 50, offset = 0, autoFetch = true } = options

  const [models, setModels] = useState<RegisteredModelType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchModels = useCallback(async (fetchOptions?: UseRegisteredModelsOptions) => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<RegisteredModelsResponse>(QUERIES.REGISTERED_MODELS, {
        stage: fetchOptions?.stage ?? stage ?? null,
        limit: fetchOptions?.limit ?? limit,
        offset: fetchOptions?.offset ?? offset,
      })
      setModels(data.registeredModels || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch registered models')
    } finally {
      setLoading(false)
    }
  }, [stage, limit, offset])

  const refetch = useCallback(async () => {
    await fetchModels()
  }, [fetchModels])

  useEffect(() => {
    if (autoFetch) {
      fetchModels()
    }
  }, [])

  return { models, loading, error, fetchModels, refetch }
}

// ============================================================================
// useRegisteredModel Hook
// ============================================================================

interface UseRegisteredModelReturn {
  model: RegisteredModelType | null
  loading: boolean
  error: string | null
  fetchModel: (id: string) => Promise<void>
  refetch: () => Promise<void>
}

interface RegisteredModelResponse {
  registeredModel: RegisteredModelType
}

export function useRegisteredModel(modelId?: string): UseRegisteredModelReturn {
  const [model, setModel] = useState<RegisteredModelType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastId, setLastId] = useState<string | undefined>(modelId)

  const fetchModel = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)
    setLastId(id)

    try {
      const data = await graphqlRequest<RegisteredModelResponse>(QUERIES.REGISTERED_MODEL, { id })
      setModel(data.registeredModel)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch registered model')
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
  }, [modelId])

  return { model, loading, error, fetchModel, refetch }
}

// ============================================================================
// useModelVersions Hook
// ============================================================================

interface UseModelVersionsOptions {
  modelId: string
  stage?: string
  limit?: number
  offset?: number
}

interface UseModelVersionsReturn {
  versions: RegistryModelVersionType[]
  loading: boolean
  error: string | null
  fetchVersions: () => Promise<void>
  refetch: () => Promise<void>
}

interface ModelVersionsResponse {
  modelVersions: RegistryModelVersionType[]
}

export function useModelVersions(options: UseModelVersionsOptions): UseModelVersionsReturn {
  const { modelId, stage, limit = 20, offset = 0 } = options

  const [versions, setVersions] = useState<RegistryModelVersionType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchVersions = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<ModelVersionsResponse>(QUERIES.MODEL_VERSIONS, {
        modelId,
        stage: stage ?? null,
        limit,
        offset,
      })
      setVersions(data.modelVersions || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch model versions')
    } finally {
      setLoading(false)
    }
  }, [modelId, stage, limit, offset])

  const refetch = useCallback(async () => {
    await fetchVersions()
  }, [fetchVersions])

  useEffect(() => {
    if (modelId) {
      fetchVersions()
    }
  }, [modelId])

  return { versions, loading, error, fetchVersions, refetch }
}

// ============================================================================
// useCompareVersions Hook
// ============================================================================

interface UseCompareVersionsReturn {
  comparison: ModelVersionComparisonType | null
  loading: boolean
  error: string | null
  compare: (modelId: string, versions: string[]) => Promise<void>
}

interface CompareVersionsResponse {
  compareModelVersions: ModelVersionComparisonType
}

export function useCompareVersions(): UseCompareVersionsReturn {
  const [comparison, setComparison] = useState<ModelVersionComparisonType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const compare = useCallback(async (modelId: string, versions: string[]) => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<CompareVersionsResponse>(QUERIES.COMPARE_MODEL_VERSIONS, {
        modelId,
        versions,
      })
      setComparison(data.compareModelVersions)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to compare versions')
    } finally {
      setLoading(false)
    }
  }, [])

  return { comparison, loading, error, compare }
}

// ============================================================================
// Registry Mutation Hooks
// ============================================================================

interface RegisterModelInput {
  name: string
  description?: string
  modelType: string
  tags?: Record<string, string>
}

interface UseRegisterModelReturn {
  registerModel: (input: RegisterModelInput) => Promise<RegisteredModelType | null>
  loading: boolean
  error: string | null
}

export function useRegisterModel(): UseRegisterModelReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const registerModel = useCallback(async (input: RegisterModelInput): Promise<RegisteredModelType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ registerModel: RegisteredModelType }>(
        MUTATIONS.REGISTER_MODEL,
        { input }
      )
      return data.registerModel
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to register model')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { registerModel, loading, error }
}

interface CreateVersionInput {
  description?: string
  mlflowRunId?: string
  metrics?: Record<string, number>
}

interface UseCreateVersionReturn {
  createVersion: (modelId: string, input: CreateVersionInput) => Promise<RegistryModelVersionType | null>
  loading: boolean
  error: string | null
}

export function useCreateVersion(): UseCreateVersionReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const createVersion = useCallback(async (modelId: string, input: CreateVersionInput): Promise<RegistryModelVersionType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ createModelVersion: RegistryModelVersionType }>(
        MUTATIONS.CREATE_MODEL_VERSION,
        { modelId, input }
      )
      return data.createModelVersion
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create version')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { createVersion, loading, error }
}

interface UsePromoteVersionReturn {
  promoteVersion: (modelId: string, version: string, stage: string) => Promise<RegistryModelVersionType | null>
  loading: boolean
  error: string | null
}

export function usePromoteVersion(): UsePromoteVersionReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const promoteVersion = useCallback(async (modelId: string, version: string, stage: string): Promise<RegistryModelVersionType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ promoteModelVersion: RegistryModelVersionType }>(
        MUTATIONS.PROMOTE_MODEL_VERSION,
        { modelId, version, stage }
      )
      return data.promoteModelVersion
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to promote version')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { promoteVersion, loading, error }
}

interface UseArchiveVersionReturn {
  archiveVersion: (modelId: string, version: string) => Promise<RegistryModelVersionType | null>
  loading: boolean
  error: string | null
}

export function useArchiveVersion(): UseArchiveVersionReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const archiveVersion = useCallback(async (modelId: string, version: string): Promise<RegistryModelVersionType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ archiveModelVersion: RegistryModelVersionType }>(
        MUTATIONS.ARCHIVE_MODEL_VERSION,
        { modelId, version }
      )
      return data.archiveModelVersion
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to archive version')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { archiveVersion, loading, error }
}

interface UseDeleteVersionReturn {
  deleteVersion: (modelId: string, version: string) => Promise<boolean>
  loading: boolean
  error: string | null
}

export function useDeleteVersion(): UseDeleteVersionReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const deleteVersion = useCallback(async (modelId: string, version: string): Promise<boolean> => {
    setLoading(true)
    setError(null)

    try {
      await graphqlRequest<{ deleteModelVersion: boolean }>(
        MUTATIONS.DELETE_MODEL_VERSION,
        { modelId, version }
      )
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete version')
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  return { deleteVersion, loading, error }
}

interface UseUpdateTagsReturn {
  updateTags: (modelId: string, tags: Record<string, string>) => Promise<RegisteredModelType | null>
  loading: boolean
  error: string | null
}

export function useUpdateTags(): UseUpdateTagsReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updateTags = useCallback(async (modelId: string, tags: Record<string, string>): Promise<RegisteredModelType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ updateModelTags: RegisteredModelType }>(
        MUTATIONS.UPDATE_MODEL_TAGS,
        { modelId, tags }
      )
      return data.updateModelTags
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update tags')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { updateTags, loading, error }
}
