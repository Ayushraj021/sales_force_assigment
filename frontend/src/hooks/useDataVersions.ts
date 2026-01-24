/**
 * Data Versioning API Hooks
 */

import { useState, useCallback, useEffect } from 'react'
import {
  graphqlRequest,
  QUERIES,
  DataVersionType,
  DataVersionComparisonType,
} from '@/lib/graphql'

// ============================================================================
// useDataVersions Hook
// ============================================================================

interface UseDataVersionsOptions {
  datasetId: string
  limit?: number
  offset?: number
  autoFetch?: boolean
}

interface UseDataVersionsReturn {
  versions: DataVersionType[]
  loading: boolean
  error: string | null
  fetchVersions: () => Promise<void>
  refetch: () => Promise<void>
}

interface DataVersionsResponse {
  dataVersions: DataVersionType[]
}

export function useDataVersions(options: UseDataVersionsOptions): UseDataVersionsReturn {
  const { datasetId, limit = 50, offset = 0, autoFetch = true } = options

  const [versions, setVersions] = useState<DataVersionType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchVersions = useCallback(async () => {
    if (!datasetId) return

    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<DataVersionsResponse>(QUERIES.DATA_VERSIONS, {
        datasetId,
        limit,
        offset,
      })
      setVersions(data.dataVersions || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data versions')
    } finally {
      setLoading(false)
    }
  }, [datasetId, limit, offset])

  const refetch = useCallback(async () => {
    await fetchVersions()
  }, [fetchVersions])

  useEffect(() => {
    if (autoFetch && datasetId) {
      fetchVersions()
    }
  }, [datasetId])

  return { versions, loading, error, fetchVersions, refetch }
}

// ============================================================================
// useDataVersion Hook
// ============================================================================

interface UseDataVersionReturn {
  version: DataVersionType | null
  loading: boolean
  error: string | null
  fetchVersion: (id: string) => Promise<void>
  refetch: () => Promise<void>
}

interface DataVersionResponse {
  dataVersion: DataVersionType
}

export function useDataVersion(versionId?: string): UseDataVersionReturn {
  const [version, setVersion] = useState<DataVersionType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastId, setLastId] = useState<string | undefined>(versionId)

  const fetchVersion = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)
    setLastId(id)

    try {
      const data = await graphqlRequest<DataVersionResponse>(QUERIES.DATA_VERSION, { id })
      setVersion(data.dataVersion)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data version')
    } finally {
      setLoading(false)
    }
  }, [])

  const refetch = useCallback(async () => {
    if (lastId) {
      await fetchVersion(lastId)
    }
  }, [fetchVersion, lastId])

  useEffect(() => {
    if (versionId) {
      fetchVersion(versionId)
    }
  }, [versionId])

  return { version, loading, error, fetchVersion, refetch }
}

// ============================================================================
// useCompareDataVersions Hook
// ============================================================================

interface UseCompareDataVersionsReturn {
  comparison: DataVersionComparisonType | null
  loading: boolean
  error: string | null
  compare: (datasetId: string, version1: string, version2: string) => Promise<void>
}

interface CompareDataVersionsResponse {
  compareDataVersions: DataVersionComparisonType
}

export function useCompareDataVersions(): UseCompareDataVersionsReturn {
  const [comparison, setComparison] = useState<DataVersionComparisonType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const compare = useCallback(async (datasetId: string, version1: string, version2: string) => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<CompareDataVersionsResponse>(QUERIES.COMPARE_DATA_VERSIONS, {
        datasetId,
        version1,
        version2,
      })
      setComparison(data.compareDataVersions)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to compare data versions')
    } finally {
      setLoading(false)
    }
  }, [])

  return { comparison, loading, error, compare }
}
