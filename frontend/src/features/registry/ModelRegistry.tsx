import { useState } from 'react'
import {
  ArchiveBoxIcon,
  ArrowPathIcon,
  ArrowUpIcon,
  ChartBarIcon,
  ClockIcon,
  CubeIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  TagIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

interface ModelVersion {
  id: string
  modelName: string
  version: string
  modelType: string
  framework: string
  stage: 'development' | 'staging' | 'production' | 'archived'
  metrics: Record<string, number>
  parameters: Record<string, unknown>
  tags: Record<string, string>
  description?: string
  checksum?: string
  fileSizeBytes?: number
  createdAt: string
  updatedAt: string
}

interface ModelEntry {
  name: string
  latestVersion: string
  versionCount: number
  productionVersion?: string
  stagingVersion?: string
  versions: ModelVersion[]
  createdAt: string
}

// Mock data
const mockModels: ModelEntry[] = [
  {
    name: 'sales_forecast',
    latestVersion: '3.2.1',
    versionCount: 12,
    productionVersion: '3.1.0',
    stagingVersion: '3.2.1',
    versions: [
      {
        id: 'v1',
        modelName: 'sales_forecast',
        version: '3.2.1',
        modelType: 'MMM',
        framework: 'pymc',
        stage: 'staging',
        metrics: { rmse: 1250.5, mape: 0.082, r2: 0.94 },
        parameters: { adstock_decay: 0.7, saturation_alpha: 2.5 },
        tags: { team: 'analytics', use_case: 'forecasting' },
        description: 'Latest MMM model with improved seasonality handling',
        createdAt: new Date(Date.now() - 86400000).toISOString(),
        updatedAt: new Date(Date.now() - 86400000).toISOString(),
      },
      {
        id: 'v2',
        modelName: 'sales_forecast',
        version: '3.1.0',
        modelType: 'MMM',
        framework: 'pymc',
        stage: 'production',
        metrics: { rmse: 1320.2, mape: 0.089, r2: 0.92 },
        parameters: { adstock_decay: 0.65, saturation_alpha: 2.2 },
        tags: { team: 'analytics', use_case: 'forecasting' },
        description: 'Production MMM model',
        createdAt: new Date(Date.now() - 604800000).toISOString(),
        updatedAt: new Date(Date.now() - 604800000).toISOString(),
      },
    ],
    createdAt: new Date(Date.now() - 2592000000).toISOString(),
  },
  {
    name: 'attribution_model',
    latestVersion: '2.0.3',
    versionCount: 8,
    productionVersion: '2.0.3',
    stagingVersion: undefined,
    versions: [
      {
        id: 'v3',
        modelName: 'attribution_model',
        version: '2.0.3',
        modelType: 'Attribution',
        framework: 'sklearn',
        stage: 'production',
        metrics: { accuracy: 0.87, precision: 0.85, recall: 0.89 },
        parameters: { model_type: 'shapley', lookback_window: 30 },
        tags: { team: 'marketing', use_case: 'attribution' },
        description: 'Multi-touch attribution with Shapley values',
        createdAt: new Date(Date.now() - 172800000).toISOString(),
        updatedAt: new Date(Date.now() - 172800000).toISOString(),
      },
    ],
    createdAt: new Date(Date.now() - 5184000000).toISOString(),
  },
  {
    name: 'demand_forecast',
    latestVersion: '1.5.0',
    versionCount: 5,
    productionVersion: undefined,
    stagingVersion: '1.5.0',
    versions: [
      {
        id: 'v4',
        modelName: 'demand_forecast',
        version: '1.5.0',
        modelType: 'TimeSeries',
        framework: 'pytorch',
        stage: 'staging',
        metrics: { mae: 523.4, mape: 0.065 },
        parameters: { hidden_layers: 3, units: 128 },
        tags: { team: 'supply_chain' },
        description: 'LSTM-based demand forecasting',
        createdAt: new Date(Date.now() - 259200000).toISOString(),
        updatedAt: new Date(Date.now() - 259200000).toISOString(),
      },
    ],
    createdAt: new Date(Date.now() - 1296000000).toISOString(),
  },
]

export function ModelRegistry() {
  const [models] = useState<ModelEntry[]>(mockModels)
  const [loading, setLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState<ModelEntry | null>(null)
  const [selectedVersion, setSelectedVersion] = useState<ModelVersion | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [stageFilter, setStageFilter] = useState<string>('all')

  const handleRefresh = async () => {
    setLoading(true)
    await new Promise(resolve => setTimeout(resolve, 1000))
    setLoading(false)
    toast.success('Registry refreshed')
  }

  const handlePromote = (modelName: string, version: string, toStage: string) => {
    toast.success(`Promoted ${modelName} v${version} to ${toStage}`)
  }

  const handleArchive = (modelName: string, version: string) => {
    toast.success(`Archived ${modelName} v${version}`)
  }

  const getStageBadge = (stage: string) => {
    const colors: Record<string, string> = {
      development: 'bg-gray-100 text-gray-800',
      staging: 'bg-yellow-100 text-yellow-800',
      production: 'bg-green-100 text-green-800',
      archived: 'bg-red-100 text-red-800',
    }
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[stage]}`}>
        {stage.charAt(0).toUpperCase() + stage.slice(1)}
      </span>
    )
  }

  const getFrameworkBadge = (framework: string) => {
    const colors: Record<string, string> = {
      pymc: 'bg-purple-100 text-purple-800',
      sklearn: 'bg-blue-100 text-blue-800',
      pytorch: 'bg-orange-100 text-orange-800',
      tensorflow: 'bg-red-100 text-red-800',
      xgboost: 'bg-green-100 text-green-800',
    }
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colors[framework] || 'bg-gray-100 text-gray-800'}`}>
        {framework}
      </span>
    )
  }

  const filteredModels = models.filter(m => {
    const matchesSearch = m.name.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStage = stageFilter === 'all' || m.versions.some(v => v.stage === stageFilter)
    return matchesSearch && matchesStage
  })

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Model Registry</h1>
          <p className="mt-1 text-sm text-gray-600">
            Manage model versions, deployments, and lifecycle stages.
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
            Register Model
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <CubeIcon className="h-8 w-8 text-gray-400" />
            <div className="ml-4">
              <p className="text-sm text-gray-500">Total Models</p>
              <p className="text-2xl font-bold text-gray-900">{models.length}</p>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4 border-l-4 border-green-500">
          <div className="flex items-center">
            <ChartBarIcon className="h-8 w-8 text-green-500" />
            <div className="ml-4">
              <p className="text-sm text-gray-500">In Production</p>
              <p className="text-2xl font-bold text-green-600">
                {models.filter(m => m.productionVersion).length}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4 border-l-4 border-yellow-500">
          <div className="flex items-center">
            <ClockIcon className="h-8 w-8 text-yellow-500" />
            <div className="ml-4">
              <p className="text-sm text-gray-500">In Staging</p>
              <p className="text-2xl font-bold text-yellow-600">
                {models.filter(m => m.stagingVersion).length}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <TagIcon className="h-8 w-8 text-gray-400" />
            <div className="ml-4">
              <p className="text-sm text-gray-500">Total Versions</p>
              <p className="text-2xl font-bold text-gray-900">
                {models.reduce((acc, m) => acc + m.versionCount, 0)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="bg-white shadow rounded-lg p-4 mb-6">
        <div className="flex flex-col md:flex-row md:items-center space-y-4 md:space-y-0 md:space-x-4">
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search models..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <select
            value={stageFilter}
            onChange={(e) => setStageFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2"
          >
            <option value="all">All Stages</option>
            <option value="development">Development</option>
            <option value="staging">Staging</option>
            <option value="production">Production</option>
            <option value="archived">Archived</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Models List */}
        <div className="lg:col-span-2 bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Registered Models</h2>
          </div>
          <ul className="divide-y divide-gray-200">
            {filteredModels.length === 0 ? (
              <li className="px-6 py-8 text-center text-gray-500">
                No models found
              </li>
            ) : (
              filteredModels.map((model) => (
                <li
                  key={model.name}
                  className={`px-6 py-4 hover:bg-gray-50 cursor-pointer ${
                    selectedModel?.name === model.name ? 'bg-blue-50' : ''
                  }`}
                  onClick={() => {
                    setSelectedModel(model)
                    setSelectedVersion(model.versions[0])
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center">
                        <CubeIcon className="h-5 w-5 text-gray-400 mr-2" />
                        <p className="text-sm font-medium text-gray-900">{model.name}</p>
                        <span className="ml-2 text-xs text-gray-500">v{model.latestVersion}</span>
                      </div>
                      <div className="flex items-center mt-2 space-x-3">
                        {model.productionVersion && (
                          <span className="text-xs text-green-600">
                            Prod: v{model.productionVersion}
                          </span>
                        )}
                        {model.stagingVersion && (
                          <span className="text-xs text-yellow-600">
                            Staging: v{model.stagingVersion}
                          </span>
                        )}
                        <span className="text-xs text-gray-500">
                          {model.versionCount} versions
                        </span>
                      </div>
                    </div>
                    <div className="text-right text-xs text-gray-500">
                      Created {new Date(model.createdAt).toLocaleDateString()}
                    </div>
                  </div>
                </li>
              ))
            )}
          </ul>
        </div>

        {/* Version Details */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Version Details</h2>
          </div>
          {selectedVersion ? (
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-medium text-gray-900">
                    {selectedVersion.modelName}
                  </h3>
                  <p className="text-lg font-bold text-gray-900">v{selectedVersion.version}</p>
                </div>
                {getStageBadge(selectedVersion.stage)}
              </div>

              <div className="space-y-4">
                <div>
                  <p className="text-xs text-gray-500 mb-1">Framework</p>
                  {getFrameworkBadge(selectedVersion.framework)}
                </div>

                {selectedVersion.description && (
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Description</p>
                    <p className="text-sm text-gray-700">{selectedVersion.description}</p>
                  </div>
                )}

                <div>
                  <p className="text-xs text-gray-500 mb-2">Metrics</p>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(selectedVersion.metrics).map(([key, value]) => (
                      <div key={key} className="bg-gray-50 rounded px-2 py-1">
                        <p className="text-xs text-gray-500">{key.toUpperCase()}</p>
                        <p className="text-sm font-medium">{typeof value === 'number' ? value.toFixed(3) : value}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-xs text-gray-500 mb-2">Tags</p>
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(selectedVersion.tags).map(([key, value]) => (
                      <span key={key} className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-700">
                        {key}: {value}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="pt-4 border-t border-gray-200">
                  <div className="flex space-x-2">
                    {selectedVersion.stage !== 'production' && (
                      <button
                        onClick={() => handlePromote(selectedVersion.modelName, selectedVersion.version, 'production')}
                        className="flex-1 btn btn-primary btn-sm"
                      >
                        <ArrowUpIcon className="h-4 w-4 mr-1" />
                        Promote
                      </button>
                    )}
                    {selectedVersion.stage !== 'archived' && (
                      <button
                        onClick={() => handleArchive(selectedVersion.modelName, selectedVersion.version)}
                        className="flex-1 btn btn-outline btn-sm"
                      >
                        <ArchiveBoxIcon className="h-4 w-4 mr-1" />
                        Archive
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 text-center text-gray-500">
              Select a model to view version details
            </div>
          )}
        </div>
      </div>

      {/* Version History */}
      {selectedModel && (
        <div className="bg-white shadow rounded-lg mt-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">
              Version History - {selectedModel.name}
            </h2>
          </div>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Version</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stage</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Framework</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Key Metrics</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {selectedModel.versions.map((version) => (
                <tr
                  key={version.id}
                  className={`hover:bg-gray-50 cursor-pointer ${
                    selectedVersion?.id === version.id ? 'bg-blue-50' : ''
                  }`}
                  onClick={() => setSelectedVersion(version)}
                >
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">
                    v{version.version}
                  </td>
                  <td className="px-6 py-4">{getStageBadge(version.stage)}</td>
                  <td className="px-6 py-4">{getFrameworkBadge(version.framework)}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {Object.entries(version.metrics).slice(0, 2).map(([k, v]) => (
                      <span key={k} className="mr-2">
                        {k}: {typeof v === 'number' ? v.toFixed(3) : v}
                      </span>
                    ))}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {new Date(version.createdAt).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <button className="text-blue-600 hover:text-blue-800 mr-3">Compare</button>
                    <button className="text-red-600 hover:text-red-800">
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
