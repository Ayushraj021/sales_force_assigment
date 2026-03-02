/**
 * System Health API Hooks
 */

import { useState, useCallback, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  version: string
  environment: string
  database: string
  redis: string
  uptime_seconds?: number
  storage?: {
    used_gb: number
    total_gb: number
  }
}

interface ServiceHealth {
  name: string
  status: 'healthy' | 'degraded' | 'unhealthy'
  latency?: number
  details?: Record<string, unknown>
}

interface UseHealthReturn {
  health: HealthStatus | null
  services: ServiceHealth[]
  loading: boolean
  error: string | null
  fetchHealth: () => Promise<void>
  refetch: () => Promise<void>
}

export function useHealth(autoRefreshMs?: number): UseHealthReturn {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [services, setServices] = useState<ServiceHealth[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchHealth = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      // Get auth token
      const authStorage = localStorage.getItem('auth-storage')
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      }

      if (authStorage) {
        const { state } = JSON.parse(authStorage)
        if (state?.accessToken) {
          headers['Authorization'] = `Bearer ${state.accessToken}`
        }
      }

      const response = await fetch(`${API_URL}/api/health/detailed`, {
        method: 'GET',
        headers,
      })

      if (!response.ok) {
        throw new Error(`Health check failed: ${response.statusText}`)
      }

      const data: HealthStatus = await response.json()
      setHealth(data)

      // Transform to services array for UI display
      const serviceList: ServiceHealth[] = [
        {
          name: 'Database',
          status: data.database === 'healthy' ? 'healthy' : 'unhealthy',
        },
        {
          name: 'Redis',
          status: data.redis === 'healthy' ? 'healthy' : 'unhealthy',
        },
      ]
      setServices(serviceList)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch health status')
    } finally {
      setLoading(false)
    }
  }, [])

  const refetch = useCallback(async () => {
    await fetchHealth()
  }, [fetchHealth])

  useEffect(() => {
    fetchHealth()

    if (autoRefreshMs && autoRefreshMs > 0) {
      const interval = setInterval(fetchHealth, autoRefreshMs)
      return () => clearInterval(interval)
    }
  }, [fetchHealth, autoRefreshMs])

  return { health, services, loading, error, fetchHealth, refetch }
}

interface UseBackgroundTasksReturn {
  tasks: BackgroundTask[]
  loading: boolean
  error: string | null
  fetchTasks: () => Promise<void>
  refetch: () => Promise<void>
}

interface BackgroundTask {
  id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress?: number
  startedAt?: string
  completedAt?: string
  error?: string
}

export function useBackgroundTasks(): UseBackgroundTasksReturn {
  const [tasks, setTasks] = useState<BackgroundTask[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchTasks = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const authStorage = localStorage.getItem('auth-storage')
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      }

      if (authStorage) {
        const { state } = JSON.parse(authStorage)
        if (state?.accessToken) {
          headers['Authorization'] = `Bearer ${state.accessToken}`
        }
      }

      const response = await fetch(`${API_URL}/api/tasks`, {
        method: 'GET',
        headers,
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch tasks: ${response.statusText}`)
      }

      const data = await response.json()
      setTasks(data.tasks || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch background tasks')
    } finally {
      setLoading(false)
    }
  }, [])

  const refetch = useCallback(async () => {
    await fetchTasks()
  }, [fetchTasks])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  return { tasks, loading, error, fetchTasks, refetch }
}
