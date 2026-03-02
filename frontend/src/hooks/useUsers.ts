/**
 * User Management API Hooks
 */

import { useState, useCallback, useEffect } from 'react'
import { graphqlRequest, QUERIES, UserType } from '@/lib/graphql'

interface UseUsersReturn {
  users: UserType[]
  loading: boolean
  error: string | null
  fetchUsers: (limit?: number, offset?: number) => Promise<void>
  refetch: () => Promise<void>
}

interface UsersResponse {
  users: UserType[]
}

export function useUsers(initialLimit = 50, initialOffset = 0): UseUsersReturn {
  const [users, setUsers] = useState<UserType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastParams, setLastParams] = useState({ limit: initialLimit, offset: initialOffset })

  const fetchUsers = useCallback(async (limit = 50, offset = 0) => {
    setLoading(true)
    setError(null)
    setLastParams({ limit, offset })

    try {
      const data = await graphqlRequest<UsersResponse>(
        QUERIES.USERS,
        { limit, offset }
      )
      setUsers(data.users || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch users')
    } finally {
      setLoading(false)
    }
  }, [])

  const refetch = useCallback(async () => {
    await fetchUsers(lastParams.limit, lastParams.offset)
  }, [fetchUsers, lastParams])

  useEffect(() => {
    fetchUsers(initialLimit, initialOffset)
  }, [])

  return { users, loading, error, fetchUsers, refetch }
}

interface UseUserReturn {
  user: UserType | null
  loading: boolean
  error: string | null
  fetchUser: (id: string) => Promise<void>
}

interface UserResponse {
  user: UserType
}

export function useUser(userId?: string): UseUserReturn {
  const [user, setUser] = useState<UserType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchUser = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<UserResponse>(
        QUERIES.USER,
        { id }
      )
      setUser(data.user)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch user')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (userId) {
      fetchUser(userId)
    }
  }, [userId, fetchUser])

  return { user, loading, error, fetchUser }
}

interface UseMeReturn {
  user: UserType | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

interface MeResponse {
  me: UserType
}

export function useMe(): UseMeReturn {
  const [user, setUser] = useState<UserType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchMe = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<MeResponse>(QUERIES.ME)
      setUser(data.me)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch user')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMe()
  }, [fetchMe])

  return { user, loading, error, refetch: fetchMe }
}
