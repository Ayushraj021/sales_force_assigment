import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import {
  CubeIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  PlayIcon,
  EllipsisVerticalIcon,
  ChartBarIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import { useModels } from '@/hooks/useModels'
import { MODEL_TYPE_LABELS } from '@/lib/constants'

const modelTypes = [
  { id: 'all', name: 'All Models' },
  { id: 'pymc_mmm', name: 'PyMC MMM' },
  { id: 'robyn_mmm', name: 'Robyn MMM' },
  { id: 'custom_mmm', name: 'Custom MMM' },
  { id: 'prophet', name: 'Prophet' },
  { id: 'arima', name: 'ARIMA' },
  { id: 'ensemble', name: 'Ensemble' },
]

const statusOptions = [
  { id: 'all', name: 'All Status' },
  { id: 'trained', name: 'Trained' },
  { id: 'training', name: 'Training' },
  { id: 'failed', name: 'Failed' },
  { id: 'draft', name: 'Draft' },
]

export function ModelList() {
  const { models: apiModels, loading, error, fetchModels, refetch } = useModels()
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')

  // Transform API models to display format
  const models = apiModels.map((model) => {
    const currentVersion = model.versions.find(v => v.isCurrent)
    const metrics = currentVersion?.metrics as Record<string, number> | undefined

    return {
      id: model.id,
      name: model.name,
      type: model.modelType,
      status: model.status,
      accuracy: metrics?.accuracy || metrics?.r2 || 0,
      lastTrained: currentVersion?.createdAt || model.updatedAt,
      createdAt: model.createdAt,
      version: model.versions.length,
      description: model.description || 'No description',
    }
  })

  const filteredModels = models.filter((model) => {
    const matchesSearch = model.name.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesType = filterType === 'all' || model.type === filterType
    const matchesStatus = filterStatus === 'all' || model.status === filterStatus
    return matchesSearch && matchesType && matchesStatus
  })

  const getTypeBadge = (type: string) => {
    const colors: Record<string, string> = {
      pymc_mmm: 'bg-purple-100 text-purple-800',
      robyn_mmm: 'bg-purple-100 text-purple-800',
      custom_mmm: 'bg-purple-100 text-purple-800',
      prophet: 'bg-green-100 text-green-800',
      arima: 'bg-green-100 text-green-800',
      sarima: 'bg-green-100 text-green-800',
      ensemble: 'bg-blue-100 text-blue-800',
    }
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[type] || 'bg-gray-100 text-gray-800'}`}>
        {MODEL_TYPE_LABELS[type] || type}
      </span>
    )
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'trained':
      case 'completed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
            <CheckCircleIcon className="h-3 w-3 mr-1" />
            Trained
          </span>
        )
      case 'training':
      case 'running':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            <ClockIcon className="h-3 w-3 mr-1 animate-spin" />
            Training
          </span>
        )
      case 'failed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
            <ExclamationCircleIcon className="h-3 w-3 mr-1" />
            Failed
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
            <ClockIcon className="h-3 w-3 mr-1" />
            {status}
          </span>
        )
    }
  }

  const formatDate = (dateString: string) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <ExclamationCircleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-red-900">Failed to load models</h3>
          <p className="mt-2 text-sm text-red-700">{error}</p>
          <button onClick={refetch} className="mt-4 btn btn-outline">
            <ArrowPathIcon className="h-5 w-5 mr-2" />
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Models</h1>
          <p className="mt-1 text-sm text-gray-600">
            Create and manage your forecasting and analytics models.
          </p>
        </div>
        <div className="flex space-x-2">
          <button onClick={refetch} className="btn btn-outline" disabled={loading}>
            <ArrowPathIcon className={`h-5 w-5 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <Link to="/models/create" className="btn btn-primary">
            <PlusIcon className="h-5 w-5 mr-2" />
            Create Model
          </Link>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4 mb-6">
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Total Models</p>
          <p className="text-2xl font-bold text-gray-900">{models.length}</p>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Trained</p>
          <p className="text-2xl font-bold text-green-600">
            {models.filter((m) => m.status === 'trained' || m.status === 'completed').length}
          </p>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Training</p>
          <p className="text-2xl font-bold text-blue-600">
            {models.filter((m) => m.status === 'training' || m.status === 'running').length}
          </p>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Avg. Accuracy</p>
          <p className="text-2xl font-bold text-gray-900">
            {models.filter((m) => m.accuracy > 0).length > 0
              ? Math.round(
                  (models.filter((m) => m.accuracy > 0).reduce((acc, m) => acc + m.accuracy, 0) /
                    models.filter((m) => m.accuracy > 0).length) *
                    100
                )
              : 0}%
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white shadow rounded-lg mb-6">
        <div className="p-4 flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search models..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input pl-10"
              />
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <FunnelIcon className="h-5 w-5 text-gray-400" />
              <select
                value={filterType}
                onChange={(e) => {
                  setFilterType(e.target.value)
                  fetchModels({ modelType: e.target.value === 'all' ? undefined : e.target.value })
                }}
                className="input py-2"
              >
                {modelTypes.map((type) => (
                  <option key={type.id} value={type.id}>
                    {type.name}
                  </option>
                ))}
              </select>
            </div>

            <select
              value={filterStatus}
              onChange={(e) => {
                setFilterStatus(e.target.value)
                fetchModels({ status: e.target.value === 'all' ? undefined : e.target.value })
              }}
              className="input py-2"
            >
              {statusOptions.map((status) => (
                <option key={status.id} value={status.id}>
                  {status.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && models.length === 0 && (
        <div className="bg-white shadow rounded-lg p-12 text-center">
          <ArrowPathIcon className="h-12 w-12 text-gray-400 mx-auto animate-spin" />
          <p className="mt-4 text-gray-500">Loading models...</p>
        </div>
      )}

      {/* Models Grid */}
      {(!loading || models.length > 0) && (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {filteredModels.length === 0 ? (
            <div className="col-span-full bg-white shadow rounded-lg p-12 text-center">
              <CubeIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No models found</h3>
              <p className="mt-1 text-sm text-gray-500">
                Get started by creating your first model.
              </p>
              <div className="mt-6">
                <Link to="/models/create" className="btn btn-primary">
                  Create Model
                </Link>
              </div>
            </div>
          ) : (
            filteredModels.map((model) => (
              <div key={model.id} className="bg-white shadow rounded-lg overflow-hidden">
                <div className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center">
                      <CubeIcon className="h-8 w-8 text-primary-600" />
                      <div className="ml-3">
                        <h3 className="text-lg font-medium text-gray-900">{model.name}</h3>
                        <p className="text-sm text-gray-500">v{model.version}</p>
                      </div>
                    </div>
                    <button className="text-gray-400 hover:text-gray-600">
                      <EllipsisVerticalIcon className="h-5 w-5" />
                    </button>
                  </div>

                  <p className="mt-4 text-sm text-gray-600 line-clamp-2">{model.description}</p>

                  <div className="mt-4 flex items-center space-x-2">
                    {getTypeBadge(model.type)}
                    {getStatusBadge(model.status)}
                  </div>

                  {(model.status === 'trained' || model.status === 'completed') && model.accuracy > 0 && (
                    <div className="mt-4 flex items-center">
                      <ChartBarIcon className="h-5 w-5 text-gray-400 mr-2" />
                      <span className="text-sm text-gray-600">
                        Accuracy: <span className="font-medium text-gray-900">{Math.round(model.accuracy * 100)}%</span>
                      </span>
                    </div>
                  )}

                  <div className="mt-2 text-sm text-gray-500">
                    {model.lastTrained ? `Last trained: ${formatDate(model.lastTrained)}` : `Created: ${formatDate(model.createdAt)}`}
                  </div>
                </div>

                <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between items-center">
                  <Link
                    to={`/models/${model.id}`}
                    className="text-sm font-medium text-primary-600 hover:text-primary-500"
                  >
                    View details
                  </Link>
                  {(model.status === 'trained' || model.status === 'completed') && (
                    <Link to="/forecasting" className="btn btn-outline btn-sm">
                      <PlayIcon className="h-4 w-4 mr-1" />
                      Run
                    </Link>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
