/**
 * Datasets API Hooks
 *
 * Hooks for fetching and managing datasets
 */

import { useState, useEffect, useCallback } from 'react'
import { graphqlRequest } from '@/lib/graphql'

// ============================================================================
// Types
// ============================================================================

export interface Channel {
  id: string
  name: string
  displayName: string | null
  channelType: string
  spendColumn: string | null
  impressionColumn: string | null
  clickColumn: string | null
}

export interface Metric {
  id: string
  name: string
  displayName: string | null
  metricType: string
  columnName: string
  isTarget: boolean
}

export interface Dataset {
  id: string
  name: string
  description: string | null
  isActive: boolean
  rowCount: number | null
  columnCount: number | null
  fileSizeBytes: number | null
  startDate: string | null
  endDate: string | null
  timeGranularity: string | null
  storageFormat: string
  columnNames: string[]
  channels: Channel[]
  metrics: Metric[]
  createdAt: string
  updatedAt: string
}

// ============================================================================
// GraphQL Queries
// ============================================================================

const DATASETS_QUERY = `
  query Datasets($isActive: Boolean, $limit: Int, $offset: Int) {
    datasets(isActive: $isActive, limit: $limit, offset: $offset) {
      id
      name
      description
      isActive
      rowCount
      columnCount
      fileSizeBytes
      startDate
      endDate
      timeGranularity
      storageFormat
      columnNames
      channels {
        id
        name
        displayName
        channelType
        spendColumn
        impressionColumn
        clickColumn
      }
      metrics {
        id
        name
        displayName
        metricType
        columnName
        isTarget
      }
      createdAt
      updatedAt
    }
  }
`

const DATASET_QUERY = `
  query Dataset($id: UUID!) {
    dataset(id: $id) {
      id
      name
      description
      isActive
      rowCount
      columnCount
      fileSizeBytes
      startDate
      endDate
      timeGranularity
      storageFormat
      columnNames
      channels {
        id
        name
        displayName
        channelType
        spendColumn
        impressionColumn
        clickColumn
      }
      metrics {
        id
        name
        displayName
        metricType
        columnName
        isTarget
      }
      createdAt
      updatedAt
    }
  }
`

const DELETE_DATASET_MUTATION = `
  mutation DeleteDataset($id: UUID!) {
    deleteDataset(id: $id)
  }
`

// ============================================================================
// Hooks
// ============================================================================

interface UseDatasetsOptions {
  autoFetch?: boolean
  isActive?: boolean
  limit?: number
  offset?: number
}

export function useDatasets(options: UseDatasetsOptions = {}) {
  const { autoFetch = true, isActive = true, limit = 50, offset = 0 } = options
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchDatasets = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ datasets: Dataset[] }>(
        DATASETS_QUERY,
        { isActive, limit, offset }
      )
      setDatasets(data.datasets)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch datasets')
    } finally {
      setLoading(false)
    }
  }, [isActive, limit, offset])

  useEffect(() => {
    if (autoFetch) {
      fetchDatasets()
    }
  }, [autoFetch, fetchDatasets])

  return { datasets, loading, error, refetch: fetchDatasets }
}

export function useDataset(datasetId?: string) {
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchDataset = useCallback(async (id?: string) => {
    const targetId = id || datasetId
    if (!targetId) return

    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ dataset: Dataset }>(
        DATASET_QUERY,
        { id: targetId }
      )
      setDataset(data.dataset)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch dataset')
    } finally {
      setLoading(false)
    }
  }, [datasetId])

  useEffect(() => {
    if (datasetId) {
      fetchDataset()
    }
  }, [datasetId, fetchDataset])

  return { dataset, loading, error, fetchDataset }
}

// Hook for dataset mutations (delete, etc.)
export function useDatasetMutations() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const deleteDataset = useCallback(async (id: string): Promise<boolean> => {
    setLoading(true)
    setError(null)

    try {
      await graphqlRequest<{ deleteDataset: boolean }>(
        DELETE_DATASET_MUTATION,
        { id }
      )
      return true
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to delete dataset'
      setError(errorMsg)
      throw new Error(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [])

  return { deleteDataset, loading, error }
}
