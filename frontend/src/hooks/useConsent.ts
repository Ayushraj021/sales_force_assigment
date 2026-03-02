/**
 * Consent Management API Hooks
 */

import { useState, useCallback, useEffect } from 'react'
import {
  graphqlRequest,
  QUERIES,
  MUTATIONS,
  ConsentRecordType,
  UserConsentStatusType,
} from '@/lib/graphql'

// ============================================================================
// useConsentRecords Hook
// ============================================================================

interface UseConsentRecordsOptions {
  userId?: string
  consentType?: string
  limit?: number
  offset?: number
  autoFetch?: boolean
}

interface UseConsentRecordsReturn {
  records: ConsentRecordType[]
  loading: boolean
  error: string | null
  fetchRecords: (options?: UseConsentRecordsOptions) => Promise<void>
  refetch: () => Promise<void>
}

interface ConsentRecordsResponse {
  consentRecords: ConsentRecordType[]
}

export function useConsentRecords(options: UseConsentRecordsOptions = {}): UseConsentRecordsReturn {
  const { userId, consentType, limit = 50, offset = 0, autoFetch = true } = options

  const [records, setRecords] = useState<ConsentRecordType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchRecords = useCallback(async (fetchOptions?: UseConsentRecordsOptions) => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<ConsentRecordsResponse>(QUERIES.CONSENT_RECORDS, {
        userId: fetchOptions?.userId ?? userId ?? null,
        consentType: fetchOptions?.consentType ?? consentType ?? null,
        limit: fetchOptions?.limit ?? limit,
        offset: fetchOptions?.offset ?? offset,
      })
      setRecords(data.consentRecords || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch consent records')
    } finally {
      setLoading(false)
    }
  }, [userId, consentType, limit, offset])

  const refetch = useCallback(async () => {
    await fetchRecords()
  }, [fetchRecords])

  useEffect(() => {
    if (autoFetch) {
      fetchRecords()
    }
  }, [])

  return { records, loading, error, fetchRecords, refetch }
}

// ============================================================================
// useConsentRecord Hook
// ============================================================================

interface UseConsentRecordReturn {
  record: ConsentRecordType | null
  loading: boolean
  error: string | null
  fetchRecord: (id: string) => Promise<void>
  refetch: () => Promise<void>
}

interface ConsentRecordResponse {
  consentRecord: ConsentRecordType
}

export function useConsentRecord(recordId?: string): UseConsentRecordReturn {
  const [record, setRecord] = useState<ConsentRecordType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastId, setLastId] = useState<string | undefined>(recordId)

  const fetchRecord = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)
    setLastId(id)

    try {
      const data = await graphqlRequest<ConsentRecordResponse>(QUERIES.CONSENT_RECORD, { id })
      setRecord(data.consentRecord)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch consent record')
    } finally {
      setLoading(false)
    }
  }, [])

  const refetch = useCallback(async () => {
    if (lastId) {
      await fetchRecord(lastId)
    }
  }, [fetchRecord, lastId])

  useEffect(() => {
    if (recordId) {
      fetchRecord(recordId)
    }
  }, [recordId])

  return { record, loading, error, fetchRecord, refetch }
}

// ============================================================================
// useUserConsentStatus Hook
// ============================================================================

interface UseUserConsentStatusReturn {
  status: UserConsentStatusType | null
  loading: boolean
  error: string | null
  fetchStatus: (userId: string) => Promise<void>
  refetch: () => Promise<void>
}

interface UserConsentStatusResponse {
  userConsentStatus: UserConsentStatusType
}

export function useUserConsentStatus(userId?: string): UseUserConsentStatusReturn {
  const [status, setStatus] = useState<UserConsentStatusType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUserId, setLastUserId] = useState<string | undefined>(userId)

  const fetchStatus = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)
    setLastUserId(id)

    try {
      const data = await graphqlRequest<UserConsentStatusResponse>(QUERIES.USER_CONSENT_STATUS, {
        userId: id,
      })
      setStatus(data.userConsentStatus)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch user consent status')
    } finally {
      setLoading(false)
    }
  }, [])

  const refetch = useCallback(async () => {
    if (lastUserId) {
      await fetchStatus(lastUserId)
    }
  }, [fetchStatus, lastUserId])

  useEffect(() => {
    if (userId) {
      fetchStatus(userId)
    }
  }, [userId])

  return { status, loading, error, fetchStatus, refetch }
}

// ============================================================================
// Consent Mutation Hooks
// ============================================================================

interface GrantConsentInput {
  userId: string
  consentType: string
  version: string
  consentText?: string
  expiresAt?: string
  ipAddress?: string
  metadata?: Record<string, unknown>
}

interface UseGrantConsentReturn {
  grantConsent: (input: GrantConsentInput) => Promise<ConsentRecordType | null>
  loading: boolean
  error: string | null
}

export function useGrantConsent(): UseGrantConsentReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const grantConsent = useCallback(async (input: GrantConsentInput): Promise<ConsentRecordType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ grantConsent: ConsentRecordType }>(
        MUTATIONS.GRANT_CONSENT,
        { input }
      )
      return data.grantConsent
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to grant consent')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { grantConsent, loading, error }
}

interface UseRevokeConsentReturn {
  revokeConsent: (id: string, reason?: string) => Promise<ConsentRecordType | null>
  loading: boolean
  error: string | null
}

export function useRevokeConsent(): UseRevokeConsentReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const revokeConsent = useCallback(async (id: string, reason?: string): Promise<ConsentRecordType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ revokeConsent: ConsentRecordType }>(
        MUTATIONS.REVOKE_CONSENT,
        { id, reason: reason ?? null }
      )
      return data.revokeConsent
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to revoke consent')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { revokeConsent, loading, error }
}

interface UpdateConsentInput {
  status?: string
  version?: string
  expiresAt?: string
  metadata?: Record<string, unknown>
}

interface UseUpdateConsentReturn {
  updateConsent: (id: string, input: UpdateConsentInput) => Promise<ConsentRecordType | null>
  loading: boolean
  error: string | null
}

export function useUpdateConsent(): UseUpdateConsentReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updateConsent = useCallback(async (id: string, input: UpdateConsentInput): Promise<ConsentRecordType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ updateConsent: ConsentRecordType }>(
        MUTATIONS.UPDATE_CONSENT,
        { id, input }
      )
      return data.updateConsent
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update consent')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { updateConsent, loading, error }
}
