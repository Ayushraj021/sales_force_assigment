import { useState, useRef, useEffect } from 'react'
import { Link } from '@tanstack/react-router'
import {
  CircleStackIcon,
  CloudArrowUpIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ClockIcon,
  EllipsisVerticalIcon,
  ArrowPathIcon,
  EyeIcon,
  TrashIcon,
  PencilIcon,
  LinkIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { useDatasets, useDatasetMutations, Dataset } from '@/hooks/useDatasets'
import { useConnectors, useSyncConnector, useDeleteConnector } from '@/hooks/useConnectors'
import { DataConnectorType } from '@/lib/graphql'

interface DataSource {
  id: string
  name: string
  type: 'file' | 'connector'
  source: string
  status: 'active' | 'syncing' | 'error' | 'pending'
  rowCount: number
  columns: number
  lastSync: string
  createdAt: string
}

// Transform dataset to data source format
function datasetToDataSource(dataset: Dataset): DataSource {
  return {
    id: dataset.id,
    name: dataset.name,
    type: 'file',
    source: dataset.storageFormat || 'CSV Upload',
    status: dataset.isActive ? 'active' : 'pending',
    rowCount: dataset.rowCount || 0,
    columns: dataset.columnCount || dataset.columnNames?.length || 0,
    lastSync: dataset.updatedAt,
    createdAt: dataset.createdAt,
  }
}

// Transform connector to data source format
function connectorToDataSource(connector: DataConnectorType): DataSource {
  return {
    id: connector.id,
    name: connector.name,
    type: 'connector',
    source: connector.sourceType.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()),
    status: connector.isActive ? 'active' : 'pending',
    rowCount: 0, // Connectors don't have row counts until synced
    columns: 0,
    lastSync: connector.updatedAt,
    createdAt: connector.createdAt,
  }
}

export function DataSourceList() {
  const { datasets, loading: datasetsLoading, error: datasetsError, refetch: refetchDatasets } = useDatasets()
  const { connectors, loading: connectorsLoading, error: connectorsError, refetch: refetchConnectors } = useConnectors()
  const { deleteDataset } = useDatasetMutations()
  const { syncConnector, loading: syncLoading } = useSyncConnector()
  const { deleteConnector } = useDeleteConnector()

  // Combine datasets and connectors into unified data sources
  const datasetSources = datasets.map(datasetToDataSource)
  const connectorSources = connectors.map(connectorToDataSource)
  const dataSources = [...datasetSources, ...connectorSources]

  const loading = datasetsLoading || connectorsLoading
  const error = datasetsError || connectorsError

  const refetch = async () => {
    await Promise.all([refetchDatasets(), refetchConnectors()])
  }
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<'all' | 'file' | 'connector'>('all')
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'syncing' | 'error'>('all')
  const [openMenuId, setOpenMenuId] = useState<string | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpenMenuId(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSync = async (id: string) => {
    setOpenMenuId(null)
    const source = dataSources.find(s => s.id === id)

    if (source?.type === 'connector') {
      try {
        toast.loading('Syncing...', { id: 'sync' })
        const result = await syncConnector(id)
        if (result?.success) {
          toast.success(`Synced ${result.recordsSynced || 0} records`, { id: 'sync' })
        } else {
          toast.error(result?.message || 'Sync failed', { id: 'sync' })
        }
        await refetchConnectors()
      } catch (error) {
        toast.error('Failed to sync connector', { id: 'sync' })
      }
    } else {
      toast.success('Dataset refresh started')
      await refetchDatasets()
    }
  }

  const handleView = (id: string) => {
    setOpenMenuId(null)
    // TODO: Navigate to dataset detail view when route is implemented
    const dataset = datasets.find((d: Dataset) => d.id === id)
    toast.success(`Viewing dataset: ${dataset?.name || id}`)
  }

  const handleEdit = (id: string) => {
    setOpenMenuId(null)
    // TODO: Navigate to dataset edit page when route is implemented
    const dataset = datasets.find((d: Dataset) => d.id === id)
    toast.success(`Editing dataset: ${dataset?.name || id}`)
  }

  const handleDelete = async (id: string) => {
    setOpenMenuId(null)

    const source = dataSources.find(s => s.id === id)
    const sourceName = source?.name || 'this source'

    if (!window.confirm(`Are you sure you want to delete "${sourceName}"? This action cannot be undone.`)) {
      return
    }

    try {
      if (source?.type === 'connector') {
        await deleteConnector(id)
        toast.success('Connector deleted successfully')
        await refetchConnectors()
      } else {
        await deleteDataset(id)
        toast.success('Data source deleted successfully')
        await refetchDatasets()
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete data source')
    }
  }

  const filteredSources = dataSources.filter((source) => {
    const matchesSearch = source.name.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesType = filterType === 'all' || source.type === filterType
    const matchesStatus = filterStatus === 'all' || source.status === filterStatus
    return matchesSearch && matchesType && matchesStatus
  })

  const getStatusBadge = (status: DataSource['status']) => {
    switch (status) {
      case 'active':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
            <CheckCircleIcon className="h-3 w-3 mr-1" />
            Active
          </span>
        )
      case 'syncing':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            <ClockIcon className="h-3 w-3 mr-1 animate-spin" />
            Syncing
          </span>
        )
      case 'error':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
            <ExclamationCircleIcon className="h-3 w-3 mr-1" />
            Error
          </span>
        )
      case 'pending':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
            <ClockIcon className="h-3 w-3 mr-1" />
            Pending
          </span>
        )
    }
  }

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat().format(num)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Data Sources</h1>
          <p className="mt-1 text-sm text-gray-600">
            Manage your data sources, uploads, and connectors.
          </p>
        </div>
        <div className="flex space-x-3">
          <Link to="/data/upload" className="btn btn-outline">
            <CloudArrowUpIcon className="h-5 w-5 mr-2" />
            Upload Data
          </Link>
          <Link to="/data/connectors" className="btn btn-primary">
            <PlusIcon className="h-5 w-5 mr-2" />
            Add Connector
          </Link>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <ArrowPathIcon className="h-8 w-8 text-primary-600 animate-spin" />
          <span className="ml-3 text-gray-600">Loading data sources...</span>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center">
            <ExclamationCircleIcon className="h-5 w-5 text-red-500 mr-2" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
          <button
            onClick={() => refetch()}
            className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Stats */}
      {!loading && (
      <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4 mb-6">
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Total Sources</p>
          <p className="text-2xl font-bold text-gray-900">{dataSources.length}</p>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Active</p>
          <p className="text-2xl font-bold text-green-600">
            {dataSources.filter((s) => s.status === 'active').length}
          </p>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Total Rows</p>
          <p className="text-2xl font-bold text-gray-900">
            {formatNumber(dataSources.reduce((acc, s) => acc + s.rowCount, 0))}
          </p>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <p className="text-sm text-gray-500">Errors</p>
          <p className="text-2xl font-bold text-red-600">
            {dataSources.filter((s) => s.status === 'error').length}
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
                placeholder="Search data sources..."
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
                onChange={(e) => setFilterType(e.target.value as typeof filterType)}
                className="input py-2"
              >
                <option value="all">All Types</option>
                <option value="file">File Uploads</option>
                <option value="connector">Connectors</option>
              </select>
            </div>

            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as typeof filterStatus)}
              className="input py-2"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="syncing">Syncing</option>
              <option value="error">Error</option>
            </select>
          </div>
        </div>
      </div>

      {/* Data Sources Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Source
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Rows
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Last Sync
              </th>
              <th className="relative px-6 py-3">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredSources.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center">
                  <CircleStackIcon className="mx-auto h-12 w-12 text-gray-400" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No data sources</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Get started by uploading data or connecting a data source.
                  </p>
                  <div className="mt-6 flex justify-center space-x-3">
                    <Link to="/data/upload" className="btn btn-outline">
                      Upload Data
                    </Link>
                    <Link to="/data/connectors" className="btn btn-primary">
                      Add Connector
                    </Link>
                  </div>
                </td>
              </tr>
            ) : (
              filteredSources.map((source) => (
                <tr key={source.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center">
                      {source.type === 'connector' ? (
                        <LinkIcon className="h-8 w-8 text-primary-600 mr-3" />
                      ) : (
                        <CircleStackIcon className="h-8 w-8 text-primary-600 mr-3" />
                      )}
                      <div>
                        <p className="text-sm font-medium text-gray-900">{source.name}</p>
                        <p className="text-sm text-gray-500">{source.columns} columns</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">{source.source}</td>
                  <td className="px-6 py-4">{getStatusBadge(source.status)}</td>
                  <td className="px-6 py-4 text-sm text-gray-900">{formatNumber(source.rowCount)}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{formatDate(source.lastSync)}</td>
                  <td className="px-6 py-4 text-right relative">
                    <div ref={openMenuId === source.id ? menuRef : null}>
                      <button
                        onClick={() => setOpenMenuId(openMenuId === source.id ? null : source.id)}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        <EllipsisVerticalIcon className="h-5 w-5" />
                      </button>
                      {openMenuId === source.id && (
                        <div className="absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50">
                          <div className="py-1">
                            <button
                              onClick={() => handleView(source.id)}
                              className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                            >
                              <EyeIcon className="h-4 w-4 mr-3" />
                              View Data
                            </button>
                            <button
                              onClick={() => handleSync(source.id)}
                              className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                            >
                              <ArrowPathIcon className="h-4 w-4 mr-3" />
                              Sync Now
                            </button>
                            <button
                              onClick={() => handleEdit(source.id)}
                              className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                            >
                              <PencilIcon className="h-4 w-4 mr-3" />
                              Edit
                            </button>
                            <hr className="my-1" />
                            <button
                              onClick={() => handleDelete(source.id)}
                              className="flex items-center w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                            >
                              <TrashIcon className="h-4 w-4 mr-3" />
                              Delete
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      </>
      )}
    </div>
  )
}
