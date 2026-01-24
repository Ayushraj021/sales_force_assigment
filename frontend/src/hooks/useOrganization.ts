/**
 * Organization API Hooks
 */

import { useState, useCallback, useEffect } from 'react'
import { graphqlRequest, QUERIES, OrganizationType } from '@/lib/graphql'

interface UseOrganizationReturn {
  organization: OrganizationType | null
  loading: boolean
  error: string | null
  fetchOrganization: (id?: string) => Promise<void>
  refetch: () => Promise<void>
}

interface OrganizationResponse {
  organization: OrganizationType
}

export function useOrganization(organizationId?: string): UseOrganizationReturn {
  const [organization, setOrganization] = useState<OrganizationType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastId, setLastId] = useState<string | undefined>(organizationId)

  const fetchOrganization = useCallback(async (id?: string) => {
    setLoading(true)
    setError(null)
    setLastId(id)

    try {
      const data = await graphqlRequest<OrganizationResponse>(
        QUERIES.ORGANIZATION,
        { id: id || null }
      )
      setOrganization(data.organization)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch organization')
    } finally {
      setLoading(false)
    }
  }, [])

  const refetch = useCallback(async () => {
    await fetchOrganization(lastId)
  }, [fetchOrganization, lastId])

  useEffect(() => {
    fetchOrganization(organizationId)
  }, [organizationId, fetchOrganization])

  return { organization, loading, error, fetchOrganization, refetch }
}
