import { useState } from 'react'
import {
  ArrowPathIcon,
  CalendarIcon,
  ClockIcon,
  PauseIcon,
  PlayIcon,
  PlusIcon,
  StopIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

interface ScheduledJob {
  id: string
  name: string
  description?: string
  jobType: string
  scheduleType: 'once' | 'interval' | 'cron' | 'daily' | 'weekly'
  intervalMinutes?: number
  cronExpression?: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused' | 'cancelled'
  lastRun?: string
  nextRun?: string
  runCount: number
  errorCount: number
  lastError?: string
  createdAt: string
}

interface JobRun {
  id: string
  jobId: string
  jobName: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  startedAt: string
  completedAt?: string
  durationSeconds?: number
  errorMessage?: string
}

interface SchedulerStatus {
  running: boolean
  totalJobs: number
  pendingJobs: number
  runningJobs: number
  failedJobs: number
  pausedJobs: number
  nextJobAt?: string
}

// Mock data
const mockJobs: ScheduledJob[] = [
  {
    id: '1',
    name: 'Daily Model Retraining',
    description: 'Retrain MMM model with latest data',
    jobType: 'model_training',
    scheduleType: 'daily',
    status: 'pending',
    lastRun: new Date(Date.now() - 86400000).toISOString(),
    nextRun: new Date(Date.now() + 3600000).toISOString(),
    runCount: 45,
    errorCount: 2,
    createdAt: new Date(Date.now() - 2592000000).toISOString(),
  },
  {
    id: '2',
    name: 'Hourly Forecast Update',
    description: 'Generate updated forecasts every hour',
    jobType: 'forecasting',
    scheduleType: 'interval',
    intervalMinutes: 60,
    status: 'running',
    lastRun: new Date(Date.now() - 1800000).toISOString(),
    nextRun: new Date(Date.now() + 1800000).toISOString(),
    runCount: 720,
    errorCount: 5,
    createdAt: new Date(Date.now() - 2592000000).toISOString(),
  },
  {
    id: '3',
    name: 'Weekly Report Generation',
    description: 'Generate weekly executive report',
    jobType: 'reporting',
    scheduleType: 'weekly',
    status: 'completed',
    lastRun: new Date(Date.now() - 172800000).toISOString(),
    nextRun: new Date(Date.now() + 432000000).toISOString(),
    runCount: 12,
    errorCount: 0,
    createdAt: new Date(Date.now() - 7776000000).toISOString(),
  },
  {
    id: '4',
    name: 'Data Quality Check',
    description: 'Validate data quality metrics',
    jobType: 'data_validation',
    scheduleType: 'cron',
    cronExpression: '0 */4 * * *',
    status: 'failed',
    lastRun: new Date(Date.now() - 7200000).toISOString(),
    nextRun: new Date(Date.now() + 7200000).toISOString(),
    runCount: 180,
    errorCount: 8,
    lastError: 'Connection timeout to database',
    createdAt: new Date(Date.now() - 5184000000).toISOString(),
  },
  {
    id: '5',
    name: 'Marketing Sync',
    description: 'Sync data from marketing platforms',
    jobType: 'data_sync',
    scheduleType: 'interval',
    intervalMinutes: 30,
    status: 'paused',
    lastRun: new Date(Date.now() - 86400000).toISOString(),
    runCount: 1440,
    errorCount: 15,
    createdAt: new Date(Date.now() - 7776000000).toISOString(),
  },
]

const mockRuns: JobRun[] = [
  {
    id: 'r1',
    jobId: '2',
    jobName: 'Hourly Forecast Update',
    status: 'running',
    startedAt: new Date(Date.now() - 300000).toISOString(),
  },
  {
    id: 'r2',
    jobId: '4',
    jobName: 'Data Quality Check',
    status: 'failed',
    startedAt: new Date(Date.now() - 7200000).toISOString(),
    completedAt: new Date(Date.now() - 7140000).toISOString(),
    durationSeconds: 60,
    errorMessage: 'Connection timeout to database',
  },
  {
    id: 'r3',
    jobId: '1',
    jobName: 'Daily Model Retraining',
    status: 'completed',
    startedAt: new Date(Date.now() - 86400000).toISOString(),
    completedAt: new Date(Date.now() - 84600000).toISOString(),
    durationSeconds: 1800,
  },
]

const mockStatus: SchedulerStatus = {
  running: true,
  totalJobs: 5,
  pendingJobs: 1,
  runningJobs: 1,
  failedJobs: 1,
  pausedJobs: 1,
  nextJobAt: new Date(Date.now() + 1800000).toISOString(),
}

export function JobScheduler() {
  const [jobs, setJobs] = useState<ScheduledJob[]>(mockJobs)
  const [runs] = useState<JobRun[]>(mockRuns)
  const [status] = useState<SchedulerStatus>(mockStatus)
  const [loading, setLoading] = useState(false)
  const [selectedJob, setSelectedJob] = useState<ScheduledJob | null>(null)
  const [filterStatus, setFilterStatus] = useState<string>('all')

  const handleRefresh = async () => {
    setLoading(true)
    await new Promise(resolve => setTimeout(resolve, 1000))
    setLoading(false)
    toast.success('Scheduler refreshed')
  }

  const handleRunNow = (jobId: string) => {
    toast.success('Job execution started')
  }

  const handlePause = (jobId: string) => {
    setJobs(prev =>
      prev.map(j => (j.id === jobId ? { ...j, status: 'paused' as const } : j))
    )
    toast.success('Job paused')
  }

  const handleResume = (jobId: string) => {
    setJobs(prev =>
      prev.map(j => (j.id === jobId ? { ...j, status: 'pending' as const } : j))
    )
    toast.success('Job resumed')
  }

  const handleCancel = (jobId: string) => {
    setJobs(prev =>
      prev.map(j => (j.id === jobId ? { ...j, status: 'cancelled' as const } : j))
    )
    toast.success('Job cancelled')
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'running':
        return <ArrowPathIcon className="h-5 w-5 text-blue-500 animate-spin" />
      case 'failed':
        return <XCircleIcon className="h-5 w-5 text-red-500" />
      case 'paused':
        return <PauseIcon className="h-5 w-5 text-yellow-500" />
      case 'cancelled':
        return <StopIcon className="h-5 w-5 text-gray-500" />
      default:
        return <ClockIcon className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-gray-100 text-gray-800',
      running: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
      paused: 'bg-yellow-100 text-yellow-800',
      cancelled: 'bg-gray-100 text-gray-500',
    }
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const getScheduleBadge = (scheduleType: string, interval?: number, cron?: string) => {
    let label = scheduleType
    if (scheduleType === 'interval' && interval) {
      label = `Every ${interval}m`
    } else if (scheduleType === 'cron' && cron) {
      label = `Cron: ${cron}`
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-purple-100 text-purple-800">
        <CalendarIcon className="h-3 w-3 mr-1" />
        {label}
      </span>
    )
  }

  const filteredJobs = jobs.filter(j => filterStatus === 'all' || j.status === filterStatus)

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Job Scheduler</h1>
          <p className="mt-1 text-sm text-gray-600">
            Manage scheduled tasks and background jobs.
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="btn btn-outline"
          >
            <ArrowPathIcon className={`h-5 w-5 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button className="btn btn-primary">
            <PlusIcon className="h-5 w-5 mr-2" />
            Create Job
          </button>
        </div>
      </div>

      {/* Scheduler Status */}
      <div className={`bg-white shadow rounded-lg p-4 mb-6 border-l-4 ${
        status.running ? 'border-green-500' : 'border-red-500'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            {status.running ? (
              <CheckCircleIcon className="h-6 w-6 text-green-500" />
            ) : (
              <ExclamationCircleIcon className="h-6 w-6 text-red-500" />
            )}
            <div className="ml-4">
              <h2 className="text-lg font-medium text-gray-900">
                Scheduler {status.running ? 'Running' : 'Stopped'}
              </h2>
              {status.nextJobAt && (
                <p className="text-sm text-gray-500">
                  Next job at: {new Date(status.nextJobAt).toLocaleString()}
                </p>
              )}
            </div>
          </div>
          <button className={`btn ${status.running ? 'btn-outline text-red-600' : 'btn-primary'}`}>
            {status.running ? (
              <>
                <StopIcon className="h-5 w-5 mr-2" />
                Stop Scheduler
              </>
            ) : (
              <>
                <PlayIcon className="h-5 w-5 mr-2" />
                Start Scheduler
              </>
            )}
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Total Jobs</p>
          <p className="text-2xl font-bold text-gray-900">{status.totalJobs}</p>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Pending</p>
          <p className="text-2xl font-bold text-gray-600">{status.pendingJobs}</p>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Running</p>
          <p className="text-2xl font-bold text-blue-600">{status.runningJobs}</p>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Failed</p>
          <p className="text-2xl font-bold text-red-600">{status.failedJobs}</p>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Paused</p>
          <p className="text-2xl font-bold text-yellow-600">{status.pausedJobs}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Jobs List */}
        <div className="lg:col-span-2 bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
            <h2 className="text-lg font-medium text-gray-900">Scheduled Jobs</h2>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="text-sm border-gray-300 rounded-md"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="paused">Paused</option>
            </select>
          </div>
          <ul className="divide-y divide-gray-200">
            {filteredJobs.map((job) => (
              <li
                key={job.id}
                className={`px-6 py-4 hover:bg-gray-50 cursor-pointer ${
                  selectedJob?.id === job.id ? 'bg-blue-50' : ''
                }`}
                onClick={() => setSelectedJob(job)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-start">
                    {getStatusIcon(job.status)}
                    <div className="ml-3">
                      <div className="flex items-center">
                        <p className="text-sm font-medium text-gray-900">{job.name}</p>
                        {getStatusBadge(job.status)}
                      </div>
                      <p className="text-sm text-gray-500 mt-1">{job.description}</p>
                      <div className="flex items-center mt-2 space-x-3">
                        {getScheduleBadge(job.scheduleType, job.intervalMinutes, job.cronExpression)}
                        <span className="text-xs text-gray-500">Runs: {job.runCount}</span>
                        {job.errorCount > 0 && (
                          <span className="text-xs text-red-600">Errors: {job.errorCount}</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleRunNow(job.id)
                      }}
                      className="btn btn-outline btn-sm"
                      disabled={job.status === 'running'}
                    >
                      <PlayIcon className="h-4 w-4" />
                    </button>
                    {job.status === 'paused' ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleResume(job.id)
                        }}
                        className="btn btn-outline btn-sm"
                      >
                        <PlayIcon className="h-4 w-4" />
                      </button>
                    ) : job.status !== 'cancelled' ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handlePause(job.id)
                        }}
                        className="btn btn-outline btn-sm"
                      >
                        <PauseIcon className="h-4 w-4" />
                      </button>
                    ) : null}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* Job Details */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Job Details</h2>
          </div>
          {selectedJob ? (
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-gray-900">{selectedJob.name}</h3>
                {getStatusBadge(selectedJob.status)}
              </div>

              <div className="space-y-4">
                <div>
                  <p className="text-xs text-gray-500">Schedule</p>
                  <p className="text-sm text-gray-900">
                    {selectedJob.scheduleType === 'cron'
                      ? selectedJob.cronExpression
                      : selectedJob.scheduleType === 'interval'
                      ? `Every ${selectedJob.intervalMinutes} minutes`
                      : selectedJob.scheduleType}
                  </p>
                </div>

                {selectedJob.nextRun && (
                  <div>
                    <p className="text-xs text-gray-500">Next Run</p>
                    <p className="text-sm text-gray-900">
                      {new Date(selectedJob.nextRun).toLocaleString()}
                    </p>
                  </div>
                )}

                {selectedJob.lastRun && (
                  <div>
                    <p className="text-xs text-gray-500">Last Run</p>
                    <p className="text-sm text-gray-900">
                      {new Date(selectedJob.lastRun).toLocaleString()}
                    </p>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-gray-500">Total Runs</p>
                    <p className="text-lg font-bold text-gray-900">{selectedJob.runCount}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Errors</p>
                    <p className={`text-lg font-bold ${selectedJob.errorCount > 0 ? 'text-red-600' : 'text-gray-900'}`}>
                      {selectedJob.errorCount}
                    </p>
                  </div>
                </div>

                {selectedJob.lastError && (
                  <div className="bg-red-50 rounded-md p-3">
                    <p className="text-xs text-red-800 font-medium">Last Error</p>
                    <p className="text-sm text-red-700 mt-1">{selectedJob.lastError}</p>
                  </div>
                )}

                <div className="pt-4 border-t border-gray-200 flex space-x-2">
                  <button className="flex-1 btn btn-outline btn-sm">Edit</button>
                  <button
                    onClick={() => handleCancel(selectedJob.id)}
                    className="flex-1 btn btn-outline btn-sm text-red-600"
                  >
                    <TrashIcon className="h-4 w-4 mr-1" />
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 text-center text-gray-500">
              Select a job to view details
            </div>
          )}
        </div>
      </div>

      {/* Recent Runs */}
      <div className="bg-white shadow rounded-lg mt-6">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Recent Job Runs</h2>
        </div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Job</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Started</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Error</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {runs.map((run) => (
              <tr key={run.id}>
                <td className="px-6 py-4 text-sm font-medium text-gray-900">{run.jobName}</td>
                <td className="px-6 py-4">{getStatusBadge(run.status)}</td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {new Date(run.startedAt).toLocaleString()}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {run.durationSeconds ? `${run.durationSeconds}s` : run.status === 'running' ? 'Running...' : '-'}
                </td>
                <td className="px-6 py-4 text-sm text-red-600">
                  {run.errorMessage || '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
