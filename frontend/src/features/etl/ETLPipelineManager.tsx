import { useState } from 'react'
import {
  ArrowPathIcon,
  PlayIcon,
  StopIcon,
  PlusIcon,
  ChevronRightIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  CubeIcon,
  ArrowsRightLeftIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

interface PipelineStep {
  id: string
  name: string
  stepType: 'extract' | 'transform' | 'load' | 'validate'
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  dependsOn: string[]
  retryCount: number
  timeoutSeconds: number
}

interface PipelineRun {
  id: string
  pipelineId: string
  pipelineName: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  startedAt: string
  completedAt?: string
  totalSteps: number
  completedSteps: number
  failedSteps: number
  errorMessage?: string
}

interface Pipeline {
  id: string
  name: string
  description?: string
  steps: PipelineStep[]
  isActive: boolean
  lastRunAt?: string
  lastRunStatus?: 'completed' | 'failed'
  runCount: number
  successCount: number
  failureCount: number
}

// Mock data
const mockPipelines: Pipeline[] = [
  {
    id: '1',
    name: 'Daily Sales Data Import',
    description: 'Imports daily sales data from BigQuery and transforms for MMM',
    steps: [
      { id: 's1', name: 'Extract from BigQuery', stepType: 'extract', status: 'completed', dependsOn: [], retryCount: 3, timeoutSeconds: 300 },
      { id: 's2', name: 'Validate Schema', stepType: 'validate', status: 'completed', dependsOn: ['s1'], retryCount: 1, timeoutSeconds: 60 },
      { id: 's3', name: 'Transform Data', stepType: 'transform', status: 'completed', dependsOn: ['s2'], retryCount: 3, timeoutSeconds: 600 },
      { id: 's4', name: 'Load to Data Warehouse', stepType: 'load', status: 'pending', dependsOn: ['s3'], retryCount: 3, timeoutSeconds: 300 },
    ],
    isActive: true,
    lastRunAt: new Date(Date.now() - 3600000).toISOString(),
    lastRunStatus: 'completed',
    runCount: 156,
    successCount: 152,
    failureCount: 4,
  },
  {
    id: '2',
    name: 'Marketing Channel Sync',
    description: 'Syncs marketing spend data from Google Ads and Meta',
    steps: [
      { id: 's1', name: 'Extract Google Ads', stepType: 'extract', status: 'pending', dependsOn: [], retryCount: 3, timeoutSeconds: 300 },
      { id: 's2', name: 'Extract Meta Ads', stepType: 'extract', status: 'pending', dependsOn: [], retryCount: 3, timeoutSeconds: 300 },
      { id: 's3', name: 'Merge & Transform', stepType: 'transform', status: 'pending', dependsOn: ['s1', 's2'], retryCount: 3, timeoutSeconds: 600 },
      { id: 's4', name: 'Load to Dataset', stepType: 'load', status: 'pending', dependsOn: ['s3'], retryCount: 3, timeoutSeconds: 300 },
    ],
    isActive: true,
    lastRunAt: new Date(Date.now() - 86400000).toISOString(),
    lastRunStatus: 'failed',
    runCount: 45,
    successCount: 42,
    failureCount: 3,
  },
]

const mockRuns: PipelineRun[] = [
  {
    id: 'r1',
    pipelineId: '1',
    pipelineName: 'Daily Sales Data Import',
    status: 'completed',
    startedAt: new Date(Date.now() - 3600000).toISOString(),
    completedAt: new Date(Date.now() - 3540000).toISOString(),
    totalSteps: 4,
    completedSteps: 4,
    failedSteps: 0,
  },
  {
    id: 'r2',
    pipelineId: '2',
    pipelineName: 'Marketing Channel Sync',
    status: 'failed',
    startedAt: new Date(Date.now() - 86400000).toISOString(),
    completedAt: new Date(Date.now() - 86340000).toISOString(),
    totalSteps: 4,
    completedSteps: 2,
    failedSteps: 1,
    errorMessage: 'Connection timeout to Google Ads API',
  },
  {
    id: 'r3',
    pipelineId: '1',
    pipelineName: 'Daily Sales Data Import',
    status: 'running',
    startedAt: new Date(Date.now() - 120000).toISOString(),
    totalSteps: 4,
    completedSteps: 2,
    failedSteps: 0,
  },
]

export function ETLPipelineManager() {
  const [pipelines, setPipelines] = useState<Pipeline[]>(mockPipelines)
  const [runs] = useState<PipelineRun[]>(mockRuns)
  const [loading, setLoading] = useState(false)
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)

  const handleRefresh = async () => {
    setLoading(true)
    await new Promise(resolve => setTimeout(resolve, 1000))
    setLoading(false)
    toast.success('Pipelines refreshed')
  }

  const handleRunPipeline = (pipelineId: string) => {
    toast.success('Pipeline execution started')
  }

  const handleToggleActive = (pipelineId: string) => {
    setPipelines(prev =>
      prev.map(p => (p.id === pipelineId ? { ...p, isActive: !p.isActive } : p))
    )
    toast.success('Pipeline status updated')
  }

  const getStepTypeIcon = (stepType: string) => {
    switch (stepType) {
      case 'extract':
        return <ArrowsRightLeftIcon className="h-4 w-4" />
      case 'transform':
        return <CubeIcon className="h-4 w-4" />
      case 'load':
        return <ArrowPathIcon className="h-4 w-4" />
      case 'validate':
        return <CheckCircleIcon className="h-4 w-4" />
      default:
        return <CubeIcon className="h-4 w-4" />
    }
  }

  const getStepStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'running':
        return <ArrowPathIcon className="h-5 w-5 text-blue-500 animate-spin" />
      case 'failed':
        return <XCircleIcon className="h-5 w-5 text-red-500" />
      case 'skipped':
        return <ExclamationCircleIcon className="h-5 w-5 text-gray-400" />
      default:
        return <ClockIcon className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      completed: 'bg-green-100 text-green-800',
      running: 'bg-blue-100 text-blue-800',
      failed: 'bg-red-100 text-red-800',
      pending: 'bg-gray-100 text-gray-800',
      skipped: 'bg-gray-100 text-gray-500',
    }
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[status] || colors.pending}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const getStepTypeBadge = (stepType: string) => {
    const colors: Record<string, string> = {
      extract: 'bg-purple-100 text-purple-800',
      transform: 'bg-blue-100 text-blue-800',
      load: 'bg-green-100 text-green-800',
      validate: 'bg-yellow-100 text-yellow-800',
    }
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colors[stepType]}`}>
        {getStepTypeIcon(stepType)}
        <span className="ml-1">{stepType.charAt(0).toUpperCase() + stepType.slice(1)}</span>
      </span>
    )
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ETL Pipeline Manager</h1>
          <p className="mt-1 text-sm text-gray-600">
            Manage data extraction, transformation, and loading pipelines.
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
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn btn-primary"
          >
            <PlusIcon className="h-5 w-5 mr-2" />
            Create Pipeline
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Total Pipelines</p>
          <p className="text-2xl font-bold text-gray-900">{pipelines.length}</p>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Active</p>
          <p className="text-2xl font-bold text-green-600">
            {pipelines.filter(p => p.isActive).length}
          </p>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Running</p>
          <p className="text-2xl font-bold text-blue-600">
            {runs.filter(r => r.status === 'running').length}
          </p>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Failed (24h)</p>
          <p className="text-2xl font-bold text-red-600">
            {runs.filter(r => r.status === 'failed').length}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pipelines List */}
        <div className="lg:col-span-2 bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Pipelines</h2>
          </div>
          <ul className="divide-y divide-gray-200">
            {pipelines.map((pipeline) => (
              <li
                key={pipeline.id}
                className={`px-6 py-4 hover:bg-gray-50 cursor-pointer ${
                  selectedPipeline?.id === pipeline.id ? 'bg-blue-50' : ''
                }`}
                onClick={() => setSelectedPipeline(pipeline)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center">
                      <p className="text-sm font-medium text-gray-900">{pipeline.name}</p>
                      <span className={`ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        pipeline.isActive ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {pipeline.isActive ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 mt-1">{pipeline.description}</p>
                    <div className="flex items-center mt-2 text-xs text-gray-500 space-x-4">
                      <span>{pipeline.steps.length} steps</span>
                      <span>Runs: {pipeline.runCount}</span>
                      <span className="text-green-600">Success: {pipeline.successCount}</span>
                      <span className="text-red-600">Failed: {pipeline.failureCount}</span>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleRunPipeline(pipeline.id)
                      }}
                      className="btn btn-primary btn-sm"
                      disabled={!pipeline.isActive}
                    >
                      <PlayIcon className="h-4 w-4" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleToggleActive(pipeline.id)
                      }}
                      className="btn btn-outline btn-sm"
                    >
                      {pipeline.isActive ? <StopIcon className="h-4 w-4" /> : <PlayIcon className="h-4 w-4" />}
                    </button>
                    <ChevronRightIcon className="h-5 w-5 text-gray-400" />
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* Pipeline Details */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Pipeline Steps</h2>
          </div>
          {selectedPipeline ? (
            <div className="p-6">
              <h3 className="text-sm font-medium text-gray-900 mb-4">{selectedPipeline.name}</h3>
              <div className="space-y-4">
                {selectedPipeline.steps.map((step, index) => (
                  <div key={step.id} className="relative">
                    {index < selectedPipeline.steps.length - 1 && (
                      <div className="absolute left-2.5 top-8 w-0.5 h-8 bg-gray-200" />
                    )}
                    <div className="flex items-start">
                      <div className="flex-shrink-0">
                        {getStepStatusIcon(step.status)}
                      </div>
                      <div className="ml-3 flex-1">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-gray-900">{step.name}</p>
                          {getStepTypeBadge(step.stepType)}
                        </div>
                        <div className="flex items-center mt-1 text-xs text-gray-500 space-x-3">
                          <span>Retries: {step.retryCount}</span>
                          <span>Timeout: {step.timeoutSeconds}s</span>
                        </div>
                        {step.dependsOn.length > 0 && (
                          <p className="text-xs text-gray-400 mt-1">
                            Depends on: {step.dependsOn.join(', ')}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-6 text-center text-gray-500">
              Select a pipeline to view steps
            </div>
          )}
        </div>
      </div>

      {/* Recent Runs */}
      <div className="bg-white shadow rounded-lg mt-6">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Recent Runs</h2>
        </div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Pipeline
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Progress
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Started
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Duration
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {runs.map((run) => (
              <tr key={run.id}>
                <td className="px-6 py-4 text-sm font-medium text-gray-900">
                  {run.pipelineName}
                </td>
                <td className="px-6 py-4">
                  {getStatusBadge(run.status)}
                </td>
                <td className="px-6 py-4">
                  <div className="w-32">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-500">
                        {run.completedSteps}/{run.totalSteps} steps
                      </span>
                    </div>
                    <div className="bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          run.status === 'failed' ? 'bg-red-500' :
                          run.status === 'completed' ? 'bg-green-500' : 'bg-blue-500'
                        }`}
                        style={{ width: `${(run.completedSteps / run.totalSteps) * 100}%` }}
                      />
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {new Date(run.startedAt).toLocaleString()}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {run.completedAt
                    ? `${Math.round((new Date(run.completedAt).getTime() - new Date(run.startedAt).getTime()) / 1000)}s`
                    : run.status === 'running' ? 'Running...' : '-'}
                </td>
                <td className="px-6 py-4 text-sm">
                  {run.status === 'running' ? (
                    <button className="text-red-600 hover:text-red-800">Cancel</button>
                  ) : run.status === 'failed' ? (
                    <button className="text-blue-600 hover:text-blue-800">Retry</button>
                  ) : (
                    <button className="text-gray-600 hover:text-gray-800">View Logs</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
