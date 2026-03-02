import { useState } from 'react'
import {
  ArrowPathIcon,
  ShieldCheckIcon,
  ShieldExclamationIcon,
  UserGroupIcon,
  ClockIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

interface ConsentRecord {
  id: string
  customerId: string
  consentType: string
  status: 'granted' | 'revoked' | 'pending' | 'expired'
  source: string
  ipAddress?: string
  grantedAt?: string
  revokedAt?: string
  expiresAt?: string
  metadata?: Record<string, unknown>
}

interface ConsentSummary {
  consentType: string
  totalRecords: number
  granted: number
  revoked: number
  pending: number
  expired: number
  grantRate: number
}

// Mock data
const mockRecords: ConsentRecord[] = [
  {
    id: '1',
    customerId: 'cust_12345',
    consentType: 'marketing_emails',
    status: 'granted',
    source: 'web_form',
    ipAddress: '192.168.1.100',
    grantedAt: new Date(Date.now() - 86400000 * 30).toISOString(),
    expiresAt: new Date(Date.now() + 86400000 * 335).toISOString(),
  },
  {
    id: '2',
    customerId: 'cust_12346',
    consentType: 'analytics_tracking',
    status: 'granted',
    source: 'cookie_banner',
    ipAddress: '192.168.1.101',
    grantedAt: new Date(Date.now() - 86400000 * 15).toISOString(),
    expiresAt: new Date(Date.now() + 86400000 * 350).toISOString(),
  },
  {
    id: '3',
    customerId: 'cust_12347',
    consentType: 'marketing_emails',
    status: 'revoked',
    source: 'preference_center',
    grantedAt: new Date(Date.now() - 86400000 * 60).toISOString(),
    revokedAt: new Date(Date.now() - 86400000 * 5).toISOString(),
  },
  {
    id: '4',
    customerId: 'cust_12348',
    consentType: 'data_sharing',
    status: 'pending',
    source: 'api',
  },
  {
    id: '5',
    customerId: 'cust_12349',
    consentType: 'personalization',
    status: 'expired',
    source: 'mobile_app',
    grantedAt: new Date(Date.now() - 86400000 * 400).toISOString(),
    expiresAt: new Date(Date.now() - 86400000 * 35).toISOString(),
  },
]

const mockSummaries: ConsentSummary[] = [
  {
    consentType: 'marketing_emails',
    totalRecords: 15420,
    granted: 12500,
    revoked: 2100,
    pending: 520,
    expired: 300,
    grantRate: 81.1,
  },
  {
    consentType: 'analytics_tracking',
    totalRecords: 28340,
    granted: 25200,
    revoked: 1800,
    pending: 340,
    expired: 1000,
    grantRate: 88.9,
  },
  {
    consentType: 'data_sharing',
    totalRecords: 8920,
    granted: 5200,
    revoked: 2800,
    pending: 420,
    expired: 500,
    grantRate: 58.3,
  },
  {
    consentType: 'personalization',
    totalRecords: 22100,
    granted: 18900,
    revoked: 2200,
    pending: 500,
    expired: 500,
    grantRate: 85.5,
  },
]

export function ConsentManagement() {
  const [records] = useState<ConsentRecord[]>(mockRecords)
  const [summaries] = useState<ConsentSummary[]>(mockSummaries)
  const [loading, setLoading] = useState(false)
  const [filterType, setFilterType] = useState<string>('all')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [searchCustomer, setSearchCustomer] = useState('')

  const handleRefresh = async () => {
    setLoading(true)
    await new Promise(resolve => setTimeout(resolve, 1000))
    setLoading(false)
    toast.success('Consent data refreshed')
  }

  const handleRevokeConsent = (recordId: string) => {
    toast.success('Consent revoked')
  }

  const handleExportData = () => {
    toast.success('Exporting consent data...')
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'granted':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'revoked':
        return <XCircleIcon className="h-5 w-5 text-red-500" />
      case 'pending':
        return <ClockIcon className="h-5 w-5 text-yellow-500" />
      case 'expired':
        return <ExclamationTriangleIcon className="h-5 w-5 text-gray-500" />
      default:
        return <ClockIcon className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      granted: 'bg-green-100 text-green-800',
      revoked: 'bg-red-100 text-red-800',
      pending: 'bg-yellow-100 text-yellow-800',
      expired: 'bg-gray-100 text-gray-500',
    }
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const consentTypes = [...new Set(records.map(r => r.consentType))]
  const filteredRecords = records.filter(r => {
    const matchesType = filterType === 'all' || r.consentType === filterType
    const matchesStatus = filterStatus === 'all' || r.status === filterStatus
    const matchesSearch = !searchCustomer || r.customerId.includes(searchCustomer)
    return matchesType && matchesStatus && matchesSearch
  })

  const totalGranted = summaries.reduce((acc, s) => acc + s.granted, 0)
  const totalRevoked = summaries.reduce((acc, s) => acc + s.revoked, 0)
  const expiringCount = records.filter(r => {
    if (!r.expiresAt) return false
    const daysUntilExpiry = (new Date(r.expiresAt).getTime() - Date.now()) / (86400000)
    return daysUntilExpiry > 0 && daysUntilExpiry <= 30
  }).length

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Consent Management</h1>
          <p className="mt-1 text-sm text-gray-600">
            Manage customer consent records and privacy compliance.
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
          <button onClick={handleExportData} className="btn btn-primary">
            <DocumentTextIcon className="h-5 w-5 mr-2" />
            Export Data
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <UserGroupIcon className="h-8 w-8 text-gray-400" />
            <div className="ml-4">
              <p className="text-sm text-gray-500">Total Records</p>
              <p className="text-2xl font-bold text-gray-900">
                {summaries.reduce((acc, s) => acc + s.totalRecords, 0).toLocaleString()}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4 border-l-4 border-green-500">
          <div className="flex items-center">
            <ShieldCheckIcon className="h-8 w-8 text-green-500" />
            <div className="ml-4">
              <p className="text-sm text-gray-500">Granted</p>
              <p className="text-2xl font-bold text-green-600">{totalGranted.toLocaleString()}</p>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4 border-l-4 border-red-500">
          <div className="flex items-center">
            <ShieldExclamationIcon className="h-8 w-8 text-red-500" />
            <div className="ml-4">
              <p className="text-sm text-gray-500">Revoked</p>
              <p className="text-2xl font-bold text-red-600">{totalRevoked.toLocaleString()}</p>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4 border-l-4 border-yellow-500">
          <div className="flex items-center">
            <ClockIcon className="h-8 w-8 text-yellow-500" />
            <div className="ml-4">
              <p className="text-sm text-gray-500">Expiring Soon</p>
              <p className="text-2xl font-bold text-yellow-600">{expiringCount}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Consent Type Summary */}
      <div className="bg-white shadow rounded-lg mb-6">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Consent by Type</h2>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {summaries.map((summary) => (
              <div key={summary.consentType} className="border rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-900 capitalize">
                  {summary.consentType.replace(/_/g, ' ')}
                </h3>
                <p className="text-2xl font-bold text-gray-900 mt-2">
                  {summary.grantRate.toFixed(1)}%
                </p>
                <p className="text-xs text-gray-500">Grant Rate</p>
                <div className="mt-3 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{ width: `${summary.grantRate}%` }}
                  />
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-green-600">{summary.granted.toLocaleString()}</span>
                    <span className="text-gray-500 ml-1">granted</span>
                  </div>
                  <div>
                    <span className="text-red-600">{summary.revoked.toLocaleString()}</span>
                    <span className="text-gray-500 ml-1">revoked</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white shadow rounded-lg p-4 mb-6">
        <div className="flex flex-col md:flex-row md:items-center space-y-4 md:space-y-0 md:space-x-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search customer ID..."
              value={searchCustomer}
              onChange={(e) => setSearchCustomer(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2"
          >
            <option value="all">All Types</option>
            {consentTypes.map(type => (
              <option key={type} value={type}>{type.replace(/_/g, ' ')}</option>
            ))}
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2"
          >
            <option value="all">All Status</option>
            <option value="granted">Granted</option>
            <option value="revoked">Revoked</option>
            <option value="pending">Pending</option>
            <option value="expired">Expired</option>
          </select>
        </div>
      </div>

      {/* Consent Records */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Consent Records</h2>
        </div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Customer</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Consent Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Granted</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Expires</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredRecords.map((record) => (
              <tr key={record.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 text-sm font-medium text-gray-900">
                  {record.customerId}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500 capitalize">
                  {record.consentType.replace(/_/g, ' ')}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center">
                    {getStatusIcon(record.status)}
                    <span className="ml-2">{getStatusBadge(record.status)}</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {record.source.replace(/_/g, ' ')}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {record.grantedAt ? new Date(record.grantedAt).toLocaleDateString() : '-'}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {record.expiresAt ? (
                    <span className={
                      new Date(record.expiresAt) < new Date() ? 'text-red-600' :
                      (new Date(record.expiresAt).getTime() - Date.now()) < 86400000 * 30 ? 'text-yellow-600' :
                      ''
                    }>
                      {new Date(record.expiresAt).toLocaleDateString()}
                    </span>
                  ) : '-'}
                </td>
                <td className="px-6 py-4 text-sm">
                  {record.status === 'granted' && (
                    <button
                      onClick={() => handleRevokeConsent(record.id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Revoke
                    </button>
                  )}
                  {record.status === 'revoked' && (
                    <span className="text-gray-400">Revoked</span>
                  )}
                  {record.status === 'pending' && (
                    <span className="text-yellow-600">Pending</span>
                  )}
                  {record.status === 'expired' && (
                    <button className="text-blue-600 hover:text-blue-800">
                      Request Renewal
                    </button>
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
