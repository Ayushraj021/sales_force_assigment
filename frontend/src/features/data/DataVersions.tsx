import { useState } from 'react'
import {
  ArrowPathIcon,
  ClockIcon,
  DocumentDuplicateIcon,
  ArrowsRightLeftIcon,
  CheckCircleIcon,
  TagIcon,
  UserIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

interface DataVersion {
  id: string
  datasetId: string
  datasetName: string
  version: number
  description?: string
  rowCount: number
  columnCount: number
  fileSizeBytes: number
  checksum: string
  createdBy: string
  createdAt: string
  changes?: {
    rowsAdded: number
    rowsRemoved: number
    rowsModified: number
    columnsAdded: string[]
    columnsRemoved: string[]
  }
  tags: string[]
}

interface VersionComparison {
  versionA: number
  versionB: number
  differences: {
    field: string
    oldValue: unknown
    newValue: unknown
  }[]
  addedRows: number
  removedRows: number
  modifiedRows: number
}

// Mock data
const mockVersions: DataVersion[] = [
  {
    id: 'v1',
    datasetId: 'ds1',
    datasetName: 'sales_data_2024',
    version: 5,
    description: 'Added Q4 2024 data',
    rowCount: 125430,
    columnCount: 45,
    fileSizeBytes: 52428800,
    checksum: 'a1b2c3d4e5f6',
    createdBy: 'john.doe@company.com',
    createdAt: new Date(Date.now() - 86400000).toISOString(),
    changes: {
      rowsAdded: 8520,
      rowsRemoved: 0,
      rowsModified: 125,
      columnsAdded: [],
      columnsRemoved: [],
    },
    tags: ['production', 'Q4-2024'],
  },
  {
    id: 'v2',
    datasetId: 'ds1',
    datasetName: 'sales_data_2024',
    version: 4,
    description: 'Data quality fixes',
    rowCount: 116910,
    columnCount: 45,
    fileSizeBytes: 48234496,
    checksum: 'f6e5d4c3b2a1',
    createdBy: 'jane.smith@company.com',
    createdAt: new Date(Date.now() - 604800000).toISOString(),
    changes: {
      rowsAdded: 0,
      rowsRemoved: 150,
      rowsModified: 2340,
      columnsAdded: [],
      columnsRemoved: [],
    },
    tags: ['production'],
  },
  {
    id: 'v3',
    datasetId: 'ds1',
    datasetName: 'sales_data_2024',
    version: 3,
    description: 'Added new marketing channels',
    rowCount: 117060,
    columnCount: 45,
    fileSizeBytes: 48500000,
    checksum: 'x9y8z7w6v5u4',
    createdBy: 'john.doe@company.com',
    createdAt: new Date(Date.now() - 1209600000).toISOString(),
    changes: {
      rowsAdded: 5200,
      rowsRemoved: 0,
      rowsModified: 0,
      columnsAdded: ['tiktok_spend', 'tiktok_impressions'],
      columnsRemoved: [],
    },
    tags: [],
  },
  {
    id: 'v4',
    datasetId: 'ds2',
    datasetName: 'marketing_spend',
    version: 8,
    description: 'Weekly sync',
    rowCount: 52000,
    columnCount: 22,
    fileSizeBytes: 15728640,
    checksum: 'm1n2o3p4q5r6',
    createdBy: 'automated',
    createdAt: new Date(Date.now() - 172800000).toISOString(),
    changes: {
      rowsAdded: 350,
      rowsRemoved: 0,
      rowsModified: 50,
      columnsAdded: [],
      columnsRemoved: [],
    },
    tags: ['automated', 'weekly'],
  },
]

export function DataVersions() {
  const [versions] = useState<DataVersion[]>(mockVersions)
  const [loading, setLoading] = useState(false)
  const [selectedDataset, setSelectedDataset] = useState<string>('all')
  const [selectedVersions, setSelectedVersions] = useState<string[]>([])
  const [showComparison, setShowComparison] = useState(false)

  const handleRefresh = async () => {
    setLoading(true)
    await new Promise(resolve => setTimeout(resolve, 1000))
    setLoading(false)
    toast.success('Versions refreshed')
  }

  const handleVersionSelect = (versionId: string) => {
    setSelectedVersions(prev => {
      if (prev.includes(versionId)) {
        return prev.filter(id => id !== versionId)
      }
      if (prev.length >= 2) {
        return [prev[1], versionId]
      }
      return [...prev, versionId]
    })
  }

  const handleCompare = () => {
    if (selectedVersions.length === 2) {
      setShowComparison(true)
      toast.success('Comparing versions')
    }
  }

  const handleRestoreVersion = (versionId: string) => {
    toast.success('Version restored')
  }

  const formatBytes = (bytes: number) => {
    if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(2)} GB`
    if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(2)} MB`
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(2)} KB`
    return `${bytes} B`
  }

  const datasets = [...new Set(versions.map(v => v.datasetName))]
  const filteredVersions = selectedDataset === 'all'
    ? versions
    : versions.filter(v => v.datasetName === selectedDataset)

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Data Versions</h1>
          <p className="mt-1 text-sm text-gray-600">
            Track and manage dataset version history.
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
          {selectedVersions.length === 2 && (
            <button onClick={handleCompare} className="btn btn-primary">
              <ArrowsRightLeftIcon className="h-5 w-5 mr-2" />
              Compare Selected
            </button>
          )}
        </div>
      </div>

      {/* Filter */}
      <div className="bg-white shadow rounded-lg p-4 mb-6">
        <div className="flex items-center space-x-4">
          <label className="text-sm font-medium text-gray-700">Dataset:</label>
          <select
            value={selectedDataset}
            onChange={(e) => setSelectedDataset(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2"
          >
            <option value="all">All Datasets</option>
            {datasets.map(ds => (
              <option key={ds} value={ds}>{ds}</option>
            ))}
          </select>
          {selectedVersions.length > 0 && (
            <span className="text-sm text-blue-600">
              {selectedVersions.length} version(s) selected for comparison
            </span>
          )}
        </div>
      </div>

      {/* Version List */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Version History</h2>
        </div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Select</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Dataset</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Version</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Changes</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Size</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredVersions.map((version) => (
              <tr
                key={version.id}
                className={selectedVersions.includes(version.id) ? 'bg-blue-50' : 'hover:bg-gray-50'}
              >
                <td className="px-6 py-4">
                  <input
                    type="checkbox"
                    checked={selectedVersions.includes(version.id)}
                    onChange={() => handleVersionSelect(version.id)}
                    className="h-4 w-4 text-blue-600 border-gray-300 rounded"
                  />
                </td>
                <td className="px-6 py-4">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{version.datasetName}</p>
                    <p className="text-xs text-gray-500">{version.rowCount.toLocaleString()} rows</p>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    v{version.version}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <p className="text-sm text-gray-900">{version.description || '-'}</p>
                  {version.tags.length > 0 && (
                    <div className="flex items-center mt-1 space-x-1">
                      <TagIcon className="h-3 w-3 text-gray-400" />
                      {version.tags.map(tag => (
                        <span key={tag} className="text-xs text-gray-500 bg-gray-100 px-1 rounded">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </td>
                <td className="px-6 py-4 text-sm">
                  {version.changes ? (
                    <div className="space-y-1">
                      {version.changes.rowsAdded > 0 && (
                        <span className="text-green-600">+{version.changes.rowsAdded.toLocaleString()} rows</span>
                      )}
                      {version.changes.rowsRemoved > 0 && (
                        <span className="text-red-600 ml-2">-{version.changes.rowsRemoved.toLocaleString()} rows</span>
                      )}
                      {version.changes.rowsModified > 0 && (
                        <span className="text-yellow-600 ml-2">~{version.changes.rowsModified.toLocaleString()} modified</span>
                      )}
                      {version.changes.columnsAdded.length > 0 && (
                        <p className="text-xs text-gray-500">
                          New columns: {version.changes.columnsAdded.join(', ')}
                        </p>
                      )}
                    </div>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {formatBytes(version.fileSizeBytes)}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center">
                    <ClockIcon className="h-4 w-4 text-gray-400 mr-1" />
                    <span className="text-sm text-gray-500">
                      {new Date(version.createdAt).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex items-center mt-1">
                    <UserIcon className="h-3 w-3 text-gray-400 mr-1" />
                    <span className="text-xs text-gray-400">{version.createdBy}</span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleRestoreVersion(version.id)}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      Restore
                    </button>
                    <button className="text-gray-600 hover:text-gray-800 text-sm">
                      <DocumentDuplicateIcon className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Comparison Modal */}
      {showComparison && selectedVersions.length === 2 && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h2 className="text-lg font-medium text-gray-900">Version Comparison</h2>
              <button
                onClick={() => setShowComparison(false)}
                className="text-gray-400 hover:text-gray-500"
              >
                &times;
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <div className="grid grid-cols-2 gap-6">
                {selectedVersions.map(vId => {
                  const version = versions.find(v => v.id === vId)
                  if (!version) return null
                  return (
                    <div key={vId} className="border rounded-lg p-4">
                      <h3 className="font-medium text-gray-900 mb-3">
                        {version.datasetName} v{version.version}
                      </h3>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-500">Rows:</span>
                          <span className="font-medium">{version.rowCount.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Columns:</span>
                          <span className="font-medium">{version.columnCount}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Size:</span>
                          <span className="font-medium">{formatBytes(version.fileSizeBytes)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Checksum:</span>
                          <span className="font-mono text-xs">{version.checksum}</span>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
              <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <h4 className="font-medium text-gray-900 mb-2">Differences Summary</h4>
                <p className="text-sm text-gray-600">
                  Select two versions to see detailed differences in row counts, schema changes, and data modifications.
                </p>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-200 flex justify-end">
              <button
                onClick={() => setShowComparison(false)}
                className="btn btn-outline"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
