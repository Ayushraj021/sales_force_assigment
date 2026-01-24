/**
 * Data Connectors API Hooks
 *
 * Hooks for managing data connectors - creating, testing, syncing, and deleting.
 */

import { useState, useEffect, useCallback } from 'react'
import {
  graphqlRequest,
  QUERIES,
  MUTATIONS,
  DataConnectorType,
  ConnectionTestResultType,
  SyncResultType,
} from '@/lib/graphql'

// ============================================================================
// Types
// ============================================================================

export interface CreateConnectorInput {
  name: string
  description?: string
  sourceType: string
  connectionConfig?: Record<string, unknown>
}

export interface UpdateConnectorInput {
  name?: string
  description?: string
  connectionConfig?: Record<string, unknown>
  isActive?: boolean
}

// ============================================================================
// Hooks
// ============================================================================

interface UseConnectorsOptions {
  autoFetch?: boolean
  isActive?: boolean
  limit?: number
  offset?: number
}

/**
 * Hook for fetching all data connectors
 */
export function useConnectors(options: UseConnectorsOptions = {}) {
  const { autoFetch = true, isActive = true, limit = 50, offset = 0 } = options
  const [connectors, setConnectors] = useState<DataConnectorType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchConnectors = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ dataConnectors: DataConnectorType[] }>(
        QUERIES.DATA_CONNECTORS,
        { isActive, limit, offset }
      )
      setConnectors(data.dataConnectors)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch connectors')
    } finally {
      setLoading(false)
    }
  }, [isActive, limit, offset])

  useEffect(() => {
    if (autoFetch) {
      fetchConnectors()
    }
  }, [autoFetch, fetchConnectors])

  return { connectors, loading, error, refetch: fetchConnectors }
}

/**
 * Hook for fetching a single connector
 */
export function useConnector(connectorId?: string) {
  const [connector, setConnector] = useState<DataConnectorType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchConnector = useCallback(async (id?: string) => {
    const targetId = id || connectorId
    if (!targetId) return

    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ dataConnector: DataConnectorType }>(
        QUERIES.DATA_CONNECTOR,
        { id: targetId }
      )
      setConnector(data.dataConnector)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch connector')
    } finally {
      setLoading(false)
    }
  }, [connectorId])

  useEffect(() => {
    if (connectorId) {
      fetchConnector()
    }
  }, [connectorId, fetchConnector])

  return { connector, loading, error, fetchConnector }
}

/**
 * Hook for creating a data connector
 */
export function useCreateConnector() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const createConnector = useCallback(async (input: CreateConnectorInput): Promise<DataConnectorType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ createDataConnector: DataConnectorType }>(
        MUTATIONS.CREATE_DATA_CONNECTOR,
        { input }
      )
      return data.createDataConnector
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to create connector'
      setError(errorMsg)
      throw new Error(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [])

  return { createConnector, loading, error }
}

/**
 * Hook for updating a data connector
 */
export function useUpdateConnector() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updateConnector = useCallback(async (
    connectorId: string,
    input: UpdateConnectorInput
  ): Promise<DataConnectorType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ updateDataConnector: DataConnectorType }>(
        MUTATIONS.UPDATE_DATA_CONNECTOR,
        { id: connectorId, input }
      )
      return data.updateDataConnector
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to update connector'
      setError(errorMsg)
      throw new Error(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [])

  return { updateConnector, loading, error }
}

/**
 * Hook for testing a data connector
 */
export function useTestConnector() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ConnectionTestResultType | null>(null)

  const testConnector = useCallback(async (connectorId: string): Promise<ConnectionTestResultType | null> => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await graphqlRequest<{ testDataConnector: ConnectionTestResultType }>(
        MUTATIONS.TEST_DATA_CONNECTOR,
        { id: connectorId }
      )
      setResult(data.testDataConnector)
      return data.testDataConnector
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to test connector'
      setError(errorMsg)
      return { success: false, message: errorMsg }
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setError(null)
    setResult(null)
  }, [])

  return { testConnector, loading, error, result, reset }
}

/**
 * Hook for syncing data from a connector
 */
export function useSyncConnector() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<SyncResultType | null>(null)

  const syncConnector = useCallback(async (
    connectorId: string,
    startDate?: string,
    endDate?: string
  ): Promise<SyncResultType | null> => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await graphqlRequest<{ syncDataConnector: SyncResultType }>(
        MUTATIONS.SYNC_DATA_CONNECTOR,
        { id: connectorId, startDate, endDate }
      )
      setResult(data.syncDataConnector)
      return data.syncDataConnector
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to sync connector'
      setError(errorMsg)
      return { success: false, message: errorMsg }
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setError(null)
    setResult(null)
  }, [])

  return { syncConnector, loading, error, result, reset }
}

/**
 * Hook for deleting a data connector
 */
export function useDeleteConnector() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const deleteConnector = useCallback(async (connectorId: string): Promise<boolean> => {
    setLoading(true)
    setError(null)

    try {
      await graphqlRequest<{ deleteDataConnector: boolean }>(
        MUTATIONS.DELETE_DATA_CONNECTOR,
        { id: connectorId }
      )
      return true
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to delete connector'
      setError(errorMsg)
      throw new Error(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [])

  return { deleteConnector, loading, error }
}

/**
 * Combined hook for connector mutations
 */
export function useConnectorMutations() {
  const { createConnector, loading: createLoading, error: createError } = useCreateConnector()
  const { updateConnector, loading: updateLoading, error: updateError } = useUpdateConnector()
  const { testConnector, loading: testLoading, error: testError, result: testResult, reset: resetTest } = useTestConnector()
  const { syncConnector, loading: syncLoading, error: syncError, result: syncResult, reset: resetSync } = useSyncConnector()
  const { deleteConnector, loading: deleteLoading, error: deleteError } = useDeleteConnector()

  return {
    createConnector,
    updateConnector,
    testConnector,
    syncConnector,
    deleteConnector,
    testResult,
    syncResult,
    resetTest,
    resetSync,
    loading: createLoading || updateLoading || testLoading || syncLoading || deleteLoading,
    error: createError || updateError || testError || syncError || deleteError,
  }
}
