/**
 * Job Scheduler API Hooks
 */

import { useState, useCallback, useEffect } from 'react'
import {
  graphqlRequest,
  QUERIES,
  MUTATIONS,
  ScheduledJobType,
  JobRunType,
  SchedulerStatusType,
} from '@/lib/graphql'

// ============================================================================
// useScheduledJobs Hook
// ============================================================================

interface UseScheduledJobsOptions {
  status?: string
  jobType?: string
  limit?: number
  offset?: number
  autoFetch?: boolean
}

interface UseScheduledJobsReturn {
  jobs: ScheduledJobType[]
  loading: boolean
  error: string | null
  fetchJobs: (options?: UseScheduledJobsOptions) => Promise<void>
  refetch: () => Promise<void>
}

interface ScheduledJobsResponse {
  scheduledJobs: ScheduledJobType[]
}

export function useScheduledJobs(options: UseScheduledJobsOptions = {}): UseScheduledJobsReturn {
  const { status, jobType, limit = 50, offset = 0, autoFetch = true } = options

  const [jobs, setJobs] = useState<ScheduledJobType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchJobs = useCallback(async (fetchOptions?: UseScheduledJobsOptions) => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<ScheduledJobsResponse>(QUERIES.SCHEDULED_JOBS, {
        status: fetchOptions?.status ?? status ?? null,
        jobType: fetchOptions?.jobType ?? jobType ?? null,
        limit: fetchOptions?.limit ?? limit,
        offset: fetchOptions?.offset ?? offset,
      })
      setJobs(data.scheduledJobs || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch scheduled jobs')
    } finally {
      setLoading(false)
    }
  }, [status, jobType, limit, offset])

  const refetch = useCallback(async () => {
    await fetchJobs()
  }, [fetchJobs])

  useEffect(() => {
    if (autoFetch) {
      fetchJobs()
    }
  }, [])

  return { jobs, loading, error, fetchJobs, refetch }
}

// ============================================================================
// useScheduledJob Hook
// ============================================================================

interface UseScheduledJobReturn {
  job: ScheduledJobType | null
  loading: boolean
  error: string | null
  fetchJob: (id: string) => Promise<void>
  refetch: () => Promise<void>
}

interface ScheduledJobResponse {
  scheduledJob: ScheduledJobType
}

export function useScheduledJob(jobId?: string): UseScheduledJobReturn {
  const [job, setJob] = useState<ScheduledJobType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastId, setLastId] = useState<string | undefined>(jobId)

  const fetchJob = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)
    setLastId(id)

    try {
      const data = await graphqlRequest<ScheduledJobResponse>(QUERIES.SCHEDULED_JOB, { id })
      setJob(data.scheduledJob)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch scheduled job')
    } finally {
      setLoading(false)
    }
  }, [])

  const refetch = useCallback(async () => {
    if (lastId) {
      await fetchJob(lastId)
    }
  }, [fetchJob, lastId])

  useEffect(() => {
    if (jobId) {
      fetchJob(jobId)
    }
  }, [jobId])

  return { job, loading, error, fetchJob, refetch }
}

// ============================================================================
// useJobRuns Hook
// ============================================================================

interface UseJobRunsOptions {
  jobId: string
  status?: string
  limit?: number
  offset?: number
}

interface UseJobRunsReturn {
  runs: JobRunType[]
  loading: boolean
  error: string | null
  fetchRuns: () => Promise<void>
  refetch: () => Promise<void>
}

interface JobRunsResponse {
  jobRuns: JobRunType[]
}

export function useJobRuns(options: UseJobRunsOptions): UseJobRunsReturn {
  const { jobId, status, limit = 20, offset = 0 } = options

  const [runs, setRuns] = useState<JobRunType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchRuns = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<JobRunsResponse>(QUERIES.JOB_RUNS, {
        jobId,
        status: status ?? null,
        limit,
        offset,
      })
      setRuns(data.jobRuns || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch job runs')
    } finally {
      setLoading(false)
    }
  }, [jobId, status, limit, offset])

  const refetch = useCallback(async () => {
    await fetchRuns()
  }, [fetchRuns])

  useEffect(() => {
    if (jobId) {
      fetchRuns()
    }
  }, [jobId])

  return { runs, loading, error, fetchRuns, refetch }
}

// ============================================================================
// useSchedulerStatus Hook
// ============================================================================

interface UseSchedulerStatusReturn {
  status: SchedulerStatusType | null
  loading: boolean
  error: string | null
  fetchStatus: () => Promise<void>
  refetch: () => Promise<void>
}

interface SchedulerStatusResponse {
  schedulerStatus: SchedulerStatusType
}

export function useSchedulerStatus(): UseSchedulerStatusReturn {
  const [status, setStatus] = useState<SchedulerStatusType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<SchedulerStatusResponse>(QUERIES.SCHEDULER_STATUS)
      setStatus(data.schedulerStatus)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch scheduler status')
    } finally {
      setLoading(false)
    }
  }, [])

  const refetch = useCallback(async () => {
    await fetchStatus()
  }, [fetchStatus])

  useEffect(() => {
    fetchStatus()
  }, [])

  return { status, loading, error, fetchStatus, refetch }
}

// ============================================================================
// Scheduler Mutation Hooks
// ============================================================================

interface CreateJobInput {
  name: string
  description?: string
  jobType: string
  schedule: string
  scheduleType: 'cron' | 'interval' | 'once'
  config?: Record<string, unknown>
}

interface UseCreateJobReturn {
  createJob: (input: CreateJobInput) => Promise<ScheduledJobType | null>
  loading: boolean
  error: string | null
}

export function useCreateJob(): UseCreateJobReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const createJob = useCallback(async (input: CreateJobInput): Promise<ScheduledJobType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ createScheduledJob: ScheduledJobType }>(
        MUTATIONS.CREATE_SCHEDULED_JOB,
        { input }
      )
      return data.createScheduledJob
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create job')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { createJob, loading, error }
}

interface UpdateJobInput {
  name?: string
  description?: string
  schedule?: string
  config?: Record<string, unknown>
}

interface UseUpdateJobReturn {
  updateJob: (id: string, input: UpdateJobInput) => Promise<ScheduledJobType | null>
  loading: boolean
  error: string | null
}

export function useUpdateJob(): UseUpdateJobReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updateJob = useCallback(async (id: string, input: UpdateJobInput): Promise<ScheduledJobType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ updateScheduledJob: ScheduledJobType }>(
        MUTATIONS.UPDATE_SCHEDULED_JOB,
        { id, input }
      )
      return data.updateScheduledJob
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update job')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { updateJob, loading, error }
}

interface UseDeleteJobReturn {
  deleteJob: (id: string) => Promise<boolean>
  loading: boolean
  error: string | null
}

export function useDeleteJob(): UseDeleteJobReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const deleteJob = useCallback(async (id: string): Promise<boolean> => {
    setLoading(true)
    setError(null)

    try {
      await graphqlRequest<{ deleteScheduledJob: boolean }>(MUTATIONS.DELETE_SCHEDULED_JOB, { id })
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete job')
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  return { deleteJob, loading, error }
}

interface UseRunJobNowReturn {
  runNow: (jobId: string) => Promise<JobRunType | null>
  loading: boolean
  error: string | null
}

export function useRunJobNow(): UseRunJobNowReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runNow = useCallback(async (jobId: string): Promise<JobRunType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ runJobNow: JobRunType }>(
        MUTATIONS.RUN_JOB_NOW,
        { jobId }
      )
      return data.runJobNow
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run job')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { runNow, loading, error }
}

interface UsePauseJobReturn {
  pauseJob: (jobId: string) => Promise<ScheduledJobType | null>
  loading: boolean
  error: string | null
}

export function usePauseJob(): UsePauseJobReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const pauseJob = useCallback(async (jobId: string): Promise<ScheduledJobType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ pauseJob: ScheduledJobType }>(
        MUTATIONS.PAUSE_JOB,
        { jobId }
      )
      return data.pauseJob
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pause job')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { pauseJob, loading, error }
}

interface UseResumeJobReturn {
  resumeJob: (jobId: string) => Promise<ScheduledJobType | null>
  loading: boolean
  error: string | null
}

export function useResumeJob(): UseResumeJobReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const resumeJob = useCallback(async (jobId: string): Promise<ScheduledJobType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ resumeJob: ScheduledJobType }>(
        MUTATIONS.RESUME_JOB,
        { jobId }
      )
      return data.resumeJob
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resume job')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { resumeJob, loading, error }
}

interface UseCancelJobRunReturn {
  cancelRun: (runId: string) => Promise<JobRunType | null>
  loading: boolean
  error: string | null
}

export function useCancelJobRun(): UseCancelJobRunReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const cancelRun = useCallback(async (runId: string): Promise<JobRunType | null> => {
    setLoading(true)
    setError(null)

    try {
      const data = await graphqlRequest<{ cancelJobRun: JobRunType }>(
        MUTATIONS.CANCEL_JOB_RUN,
        { runId }
      )
      return data.cancelJobRun
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel run')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { cancelRun, loading, error }
}
