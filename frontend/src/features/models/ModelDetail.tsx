import { useState } from 'react'
import { Link, useParams } from '@tanstack/react-router'
import {
  ArrowLeftIcon,
  CubeIcon,
  ChartBarIcon,
  ClockIcon,
  Cog6ToothIcon,
  PlayIcon,
  TrashIcon,
  ArrowPathIcon,
  DocumentDuplicateIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { useModel } from '@/hooks/useModels'
import { MODEL_TYPE_LABELS } from '@/lib/constants'

export function ModelDetail() {
  const { id } = useParams({ strict: false })
  const { model, loading, error, refetch } = useModel(id)
  const [activeTab, setActiveTab] = useState<'overview' | 'parameters' | 'history' | 'features'>('overview')

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

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
            <ExclamationTriangleIcon className="h-3 w-3 mr-1" />
            Failed
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
            {status}
          </span>
        )
    }
  }

  const tabs = [
    { id: 'overview', name: 'Overview' },
    { id: 'parameters', name: 'Parameters' },
    { id: 'history', name: 'Training History' },
    { id: 'features', name: 'Feature Importance' },
  ]

  if (loading && !model) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="bg-white shadow rounded-lg p-12 text-center">
          <ArrowPathIcon className="h-12 w-12 text-gray-400 mx-auto animate-spin" />
          <p className="mt-4 text-gray-500">Loading model details...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto">
        <Link
          to="/models"
          className="flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="h-4 w-4 mr-1" />
          Back to models
        </Link>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <ExclamationCircleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-red-900">Failed to load model</h3>
          <p className="mt-2 text-sm text-red-700">{error}</p>
          <button onClick={refetch} className="mt-4 btn btn-outline">
            <ArrowPathIcon className="h-5 w-5 mr-2" />
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!model) {
    return (
      <div className="max-w-7xl mx-auto">
        <Link
          to="/models"
          className="flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="h-4 w-4 mr-1" />
          Back to models
        </Link>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <ExclamationCircleIcon className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-yellow-900">Model not found</h3>
          <p className="mt-2 text-sm text-yellow-700">
            The model you're looking for doesn't exist.
          </p>
        </div>
      </div>
    )
  }

  // Get current version and its metrics
  const currentVersion = model.versions.find(v => v.isCurrent) || model.versions[0]
  const metrics = currentVersion?.metrics as Record<string, number> | undefined

  // Build feature importance from parameters
  const featureImportance = model.parameters
    ?.filter(p => p.parameterType === 'coefficient' || p.parameterType === 'effect')
    .map(p => ({
      feature: p.parameterName,
      importance: Math.abs(p.value || p.posteriorMean || 0),
    }))
    .sort((a, b) => b.importance - a.importance)
    .slice(0, 10) || []

  // Normalize importance values
  const maxImportance = Math.max(...featureImportance.map(f => f.importance), 1)
  featureImportance.forEach(f => {
    f.importance = f.importance / maxImportance
  })

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/models"
          className="flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="h-4 w-4 mr-1" />
          Back to models
        </Link>

        <div className="flex items-start justify-between">
          <div className="flex items-center">
            <CubeIcon className="h-12 w-12 text-primary-600" />
            <div className="ml-4">
              <div className="flex items-center space-x-3">
                <h1 className="text-2xl font-bold text-gray-900">{model.name}</h1>
                {getTypeBadge(model.modelType)}
                {getStatusBadge(model.status)}
              </div>
              <p className="mt-1 text-sm text-gray-500">
                Version {model.versions.length} | Last updated: {formatDate(model.updatedAt)}
              </p>
            </div>
          </div>

          <div className="flex space-x-3">
            <button onClick={refetch} className="btn btn-outline" disabled={loading}>
              <ArrowPathIcon className={`h-5 w-5 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button className="btn btn-outline">
              <DocumentDuplicateIcon className="h-5 w-5 mr-2" />
              Clone
            </button>
            <button
              onClick={() => toast.success('Model training started!')}
              className="btn btn-primary"
            >
              <ArrowPathIcon className="h-5 w-5 mr-2" />
              Retrain
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Metrics */}
          <div className="lg:col-span-2">
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Model Metrics</h2>
              {metrics ? (
                <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
                  {metrics.accuracy !== undefined && (
                    <div>
                      <p className="text-sm text-gray-500">Accuracy</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {Math.round(metrics.accuracy * 100)}%
                      </p>
                    </div>
                  )}
                  {metrics.rmse !== undefined && (
                    <div>
                      <p className="text-sm text-gray-500">RMSE</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {metrics.rmse.toFixed(2)}
                      </p>
                    </div>
                  )}
                  {metrics.mape !== undefined && (
                    <div>
                      <p className="text-sm text-gray-500">MAPE</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {(metrics.mape * 100).toFixed(1)}%
                      </p>
                    </div>
                  )}
                  {metrics.r2 !== undefined && (
                    <div>
                      <p className="text-sm text-gray-500">R-squared</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {metrics.r2.toFixed(2)}
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-gray-500">No metrics available yet</p>
              )}
            </div>

            <div className="bg-white shadow rounded-lg p-6 mt-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Description</h2>
              <p className="text-gray-600">{model.description || 'No description available'}</p>
            </div>
          </div>

          {/* Info Card */}
          <div className="space-y-6">
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Model Info</h2>
              <dl className="space-y-4">
                <div>
                  <dt className="text-sm text-gray-500">Model Type</dt>
                  <dd className="text-sm font-medium text-gray-900">{MODEL_TYPE_LABELS[model.modelType] || model.modelType}</dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Created</dt>
                  <dd className="text-sm font-medium text-gray-900">{formatDate(model.createdAt)}</dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Training Runs</dt>
                  <dd className="text-sm font-medium text-gray-900">{model.versions.length}</dd>
                </div>
              </dl>
            </div>

            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h2>
              <div className="space-y-3">
                <Link to="/forecasting" className="btn btn-outline w-full justify-center">
                  <PlayIcon className="h-5 w-5 mr-2" />
                  Generate Forecast
                </Link>
                <button className="btn btn-outline w-full justify-center">
                  <Cog6ToothIcon className="h-5 w-5 mr-2" />
                  Edit Parameters
                </button>
                <button className="btn btn-outline w-full justify-center text-red-600 hover:text-red-700 hover:bg-red-50">
                  <TrashIcon className="h-5 w-5 mr-2" />
                  Delete Model
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'parameters' && (
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Model Parameters</h2>
          {model.hyperparameters && Object.keys(model.hyperparameters).length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Parameter
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Value
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {Object.entries(model.hyperparameters as Record<string, unknown>).map(([key, value]) => (
                    <tr key={key}>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {key.replace(/([A-Z])/g, ' $1').replace(/_/g, ' ').trim()}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{String(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500">No parameters configured</p>
          )}

          {/* Adstock Configs */}
          {model.adstockConfigs && model.adstockConfigs.length > 0 && (
            <div className="mt-8">
              <h3 className="text-md font-medium text-gray-900 mb-4">Adstock Configurations</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {model.adstockConfigs.map((config) => (
                  <div key={config.id} className="border border-gray-200 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900">{config.channelName}</h4>
                    <dl className="mt-2 text-sm space-y-1">
                      <div className="flex justify-between">
                        <dt className="text-gray-500">Type</dt>
                        <dd className="text-gray-900">{config.adstockType}</dd>
                      </div>
                      {config.decayRate !== undefined && (
                        <div className="flex justify-between">
                          <dt className="text-gray-500">Decay Rate</dt>
                          <dd className="text-gray-900">{config.decayRate.toFixed(3)}</dd>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <dt className="text-gray-500">Max Lag</dt>
                        <dd className="text-gray-900">{config.maxLag}</dd>
                      </div>
                    </dl>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'history' && (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          {model.versions.length > 0 ? (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Version
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Metrics
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Duration
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {model.versions.map((version) => {
                  const versionMetrics = version.metrics as Record<string, number> | undefined
                  return (
                    <tr key={version.id}>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">
                        {version.version}
                        {version.isCurrent && (
                          <span className="ml-2 text-xs text-primary-600">(current)</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {version.status === 'completed' ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            <CheckCircleIcon className="h-3 w-3 mr-1" />
                            Completed
                          </span>
                        ) : version.status === 'failed' ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            <ExclamationTriangleIcon className="h-3 w-3 mr-1" />
                            Failed
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            {version.status}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {versionMetrics?.accuracy !== undefined
                          ? `${Math.round(versionMetrics.accuracy * 100)}%`
                          : versionMetrics?.r2 !== undefined
                          ? `R²: ${versionMetrics.r2.toFixed(2)}`
                          : '-'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {version.trainingDurationSeconds
                          ? `${Math.round(version.trainingDurationSeconds / 60)} min`
                          : '-'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">{formatDate(version.createdAt)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          ) : (
            <div className="p-8 text-center text-gray-500">No training history available</div>
          )}
        </div>
      )}

      {activeTab === 'features' && (
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Feature Importance</h2>
          {featureImportance.length > 0 ? (
            <div className="space-y-4">
              {featureImportance.map((item) => (
                <div key={item.feature}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-gray-900">{item.feature}</span>
                    <span className="text-gray-500">{Math.round(item.importance * 100)}%</span>
                  </div>
                  <div className="bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-primary-600 h-2 rounded-full"
                      style={{ width: `${item.importance * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No feature importance data available</p>
          )}
        </div>
      )}
    </div>
  )
}
