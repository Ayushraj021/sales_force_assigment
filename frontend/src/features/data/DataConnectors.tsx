import { useState } from 'react'
import { useForm } from 'react-hook-form'
import {
  CloudIcon,
  ServerIcon,
  ChartBarIcon,
  CurrencyDollarIcon,
  GlobeAltIcon,
  BuildingOfficeIcon,
  CheckCircleIcon,
  ArrowLeftIcon,
  ArrowPathIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { useCreateConnector, useTestConnector, useConnectors } from '@/hooks/useConnectors'

interface Connector {
  id: string
  name: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  category: 'warehouse' | 'ads' | 'analytics' | 'crm' | 'external'
  fields: ConnectorField[]
}

interface ConnectorField {
  name: string
  label: string
  type: 'text' | 'password' | 'select' | 'textarea'
  required: boolean
  placeholder?: string
  options?: { value: string; label: string }[]
}

const connectors: Connector[] = [
  {
    id: 'bigquery',
    name: 'Google BigQuery',
    description: 'Connect to Google BigQuery for large-scale data warehouse',
    icon: ServerIcon,
    category: 'warehouse',
    fields: [
      { name: 'projectId', label: 'Project ID', type: 'text', required: true, placeholder: 'my-project-123' },
      { name: 'datasetId', label: 'Dataset ID', type: 'text', required: true, placeholder: 'my_dataset' },
      { name: 'credentials', label: 'Service Account JSON', type: 'textarea', required: true, placeholder: 'Paste your service account JSON key' },
    ],
  },
  {
    id: 'snowflake',
    name: 'Snowflake',
    description: 'Connect to Snowflake cloud data warehouse',
    icon: ServerIcon,
    category: 'warehouse',
    fields: [
      { name: 'account', label: 'Account', type: 'text', required: true, placeholder: 'xy12345.us-east-1' },
      { name: 'warehouse', label: 'Warehouse', type: 'text', required: true, placeholder: 'COMPUTE_WH' },
      { name: 'database', label: 'Database', type: 'text', required: true, placeholder: 'MY_DATABASE' },
      { name: 'schema', label: 'Schema', type: 'text', required: true, placeholder: 'PUBLIC' },
      { name: 'username', label: 'Username', type: 'text', required: true },
      { name: 'password', label: 'Password', type: 'password', required: true },
    ],
  },
  {
    id: 'databricks',
    name: 'Databricks',
    description: 'Connect to Databricks lakehouse platform',
    icon: ServerIcon,
    category: 'warehouse',
    fields: [
      { name: 'host', label: 'Host', type: 'text', required: true, placeholder: 'adb-xxxx.azuredatabricks.net' },
      { name: 'httpPath', label: 'HTTP Path', type: 'text', required: true, placeholder: '/sql/1.0/warehouses/xxx' },
      { name: 'token', label: 'Access Token', type: 'password', required: true },
    ],
  },
  {
    id: 'redshift',
    name: 'Amazon Redshift',
    description: 'Connect to Amazon Redshift data warehouse',
    icon: ServerIcon,
    category: 'warehouse',
    fields: [
      { name: 'host', label: 'Host', type: 'text', required: true, placeholder: 'cluster.xxxxx.region.redshift.amazonaws.com' },
      { name: 'port', label: 'Port', type: 'text', required: true, placeholder: '5439' },
      { name: 'database', label: 'Database', type: 'text', required: true },
      { name: 'username', label: 'Username', type: 'text', required: true },
      { name: 'password', label: 'Password', type: 'password', required: true },
    ],
  },
  {
    id: 'google-ads',
    name: 'Google Ads',
    description: 'Import campaign data from Google Ads',
    icon: CurrencyDollarIcon,
    category: 'ads',
    fields: [
      { name: 'customerId', label: 'Customer ID', type: 'text', required: true, placeholder: '123-456-7890' },
      { name: 'developerToken', label: 'Developer Token', type: 'password', required: true },
      { name: 'refreshToken', label: 'Refresh Token', type: 'password', required: true },
    ],
  },
  {
    id: 'meta-ads',
    name: 'Meta Ads',
    description: 'Import campaign data from Facebook & Instagram Ads',
    icon: CurrencyDollarIcon,
    category: 'ads',
    fields: [
      { name: 'accountId', label: 'Ad Account ID', type: 'text', required: true, placeholder: 'act_123456789' },
      { name: 'accessToken', label: 'Access Token', type: 'password', required: true },
    ],
  },
  {
    id: 'google-analytics',
    name: 'Google Analytics',
    description: 'Import web analytics data from GA4',
    icon: ChartBarIcon,
    category: 'analytics',
    fields: [
      { name: 'propertyId', label: 'Property ID', type: 'text', required: true, placeholder: '123456789' },
      { name: 'credentials', label: 'Service Account JSON', type: 'textarea', required: true },
    ],
  },
  {
    id: 'salesforce',
    name: 'Salesforce',
    description: 'Import CRM data from Salesforce',
    icon: BuildingOfficeIcon,
    category: 'crm',
    fields: [
      { name: 'instanceUrl', label: 'Instance URL', type: 'text', required: true, placeholder: 'https://yourcompany.salesforce.com' },
      { name: 'username', label: 'Username', type: 'text', required: true },
      { name: 'password', label: 'Password', type: 'password', required: true },
      { name: 'securityToken', label: 'Security Token', type: 'password', required: true },
    ],
  },
  {
    id: 'hubspot',
    name: 'HubSpot',
    description: 'Import marketing and CRM data from HubSpot',
    icon: BuildingOfficeIcon,
    category: 'crm',
    fields: [
      { name: 'accessToken', label: 'Private App Token', type: 'password', required: true },
    ],
  },
  {
    id: 'external-data',
    name: 'External Data',
    description: 'Import weather, economic, and social data',
    icon: GlobeAltIcon,
    category: 'external',
    fields: [
      {
        name: 'dataType',
        label: 'Data Type',
        type: 'select',
        required: true,
        options: [
          { value: 'weather', label: 'Weather Data' },
          { value: 'economic', label: 'Economic Indicators' },
          { value: 'social', label: 'Social Trends' },
        ],
      },
      { name: 'region', label: 'Region', type: 'text', required: true, placeholder: 'US' },
      { name: 'apiKey', label: 'API Key (if required)', type: 'password', required: false },
    ],
  },
]

const categories = [
  { id: 'all', name: 'All Connectors' },
  { id: 'warehouse', name: 'Data Warehouses' },
  { id: 'ads', name: 'Advertising Platforms' },
  { id: 'analytics', name: 'Analytics' },
  { id: 'crm', name: 'CRM' },
  { id: 'external', name: 'External Data' },
]

export function DataConnectors() {
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [selectedConnector, setSelectedConnector] = useState<Connector | null>(null)
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')

  const { register, handleSubmit, reset, formState: { errors }, getValues } = useForm()

  // Hooks
  const { createConnector, loading: createLoading } = useCreateConnector()
  const { testConnector, loading: testLoading, result: testResult, reset: resetTest } = useTestConnector()
  const { refetch: refetchConnectors } = useConnectors({ autoFetch: false })

  const filteredConnectors = connectors.filter(
    (c) => selectedCategory === 'all' || c.category === selectedCategory
  )

  const isConnecting = createLoading || testLoading

  // Test connection before submitting
  const handleTestConnection = async () => {
    if (!selectedConnector) return

    setTestStatus('testing')
    resetTest()

    // Create a temporary connector to test
    try {
      const formData = getValues()
      const result = await createConnector({
        name: `Test - ${selectedConnector.name}`,
        description: 'Temporary connector for testing',
        sourceType: selectedConnector.id.replace('-', '_'),
        connectionConfig: formData,
      })

      if (result) {
        const testRes = await testConnector(result.id)
        if (testRes?.success) {
          setTestStatus('success')
          toast.success('Connection test successful!')
        } else {
          setTestStatus('error')
          toast.error(testRes?.message || 'Connection test failed')
        }
      }
    } catch (error) {
      setTestStatus('error')
      toast.error('Failed to test connection')
    }
  }

  const onSubmit = async (data: Record<string, string>) => {
    if (!selectedConnector) return

    try {
      const result = await createConnector({
        name: selectedConnector.name,
        description: selectedConnector.description,
        sourceType: selectedConnector.id.replace('-', '_'),
        connectionConfig: data,
      })

      if (result) {
        toast.success(`${selectedConnector.name} connected successfully!`)
        setSelectedConnector(null)
        setTestStatus('idle')
        reset()
        refetchConnectors()
      }
    } catch (error) {
      toast.error('Failed to connect. Please check your credentials.')
    }
  }

  if (selectedConnector) {
    return (
      <div className="max-w-2xl mx-auto">
        <button
          onClick={() => {
            setSelectedConnector(null)
            reset()
          }}
          className="flex items-center text-sm text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeftIcon className="h-4 w-4 mr-1" />
          Back to connectors
        </button>

        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center">
              <selectedConnector.icon className="h-8 w-8 text-primary-600 mr-3" />
              <div>
                <h2 className="text-lg font-medium text-gray-900">{selectedConnector.name}</h2>
                <p className="text-sm text-gray-500">{selectedConnector.description}</p>
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="px-6 py-6 space-y-6">
            {selectedConnector.fields.map((field) => (
              <div key={field.name}>
                <label htmlFor={field.name} className="label">
                  {field.label}
                  {field.required && <span className="text-red-500 ml-1">*</span>}
                </label>
                {field.type === 'select' ? (
                  <select
                    id={field.name}
                    className="input"
                    {...register(field.name, { required: field.required && `${field.label} is required` })}
                  >
                    <option value="">Select {field.label}</option>
                    {field.options?.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                ) : field.type === 'textarea' ? (
                  <textarea
                    id={field.name}
                    rows={4}
                    className="input"
                    placeholder={field.placeholder}
                    {...register(field.name, { required: field.required && `${field.label} is required` })}
                  />
                ) : (
                  <input
                    id={field.name}
                    type={field.type}
                    className="input"
                    placeholder={field.placeholder}
                    {...register(field.name, { required: field.required && `${field.label} is required` })}
                  />
                )}
                {errors[field.name] && (
                  <p className="mt-1 text-sm text-red-600">{errors[field.name]?.message as string}</p>
                )}
              </div>
            ))}

            {/* Test Result Status */}
            {testStatus !== 'idle' && (
              <div className={`p-4 rounded-lg ${
                testStatus === 'testing' ? 'bg-blue-50 text-blue-700' :
                testStatus === 'success' ? 'bg-green-50 text-green-700' :
                'bg-red-50 text-red-700'
              }`}>
                <div className="flex items-center">
                  {testStatus === 'testing' && (
                    <>
                      <ArrowPathIcon className="h-5 w-5 mr-2 animate-spin" />
                      Testing connection...
                    </>
                  )}
                  {testStatus === 'success' && (
                    <>
                      <CheckCircleIcon className="h-5 w-5 mr-2" />
                      Connection test successful!
                    </>
                  )}
                  {testStatus === 'error' && (
                    <>
                      <ExclamationCircleIcon className="h-5 w-5 mr-2" />
                      {testResult?.message || 'Connection test failed'}
                    </>
                  )}
                </div>
              </div>
            )}

            <div className="pt-4 flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => {
                  setSelectedConnector(null)
                  setTestStatus('idle')
                  reset()
                }}
                className="btn btn-outline"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleTestConnection}
                disabled={isConnecting}
                className="btn btn-outline"
              >
                {testLoading ? (
                  <>
                    <ArrowPathIcon className="h-4 w-4 mr-2 animate-spin" />
                    Testing...
                  </>
                ) : (
                  'Test Connection'
                )}
              </button>
              <button type="submit" disabled={isConnecting} className="btn btn-primary">
                {createLoading ? 'Connecting...' : 'Connect'}
              </button>
            </div>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Data Connectors</h1>
        <p className="mt-1 text-sm text-gray-600">
          Connect your data sources to automatically sync data for analysis.
        </p>
      </div>

      {/* Category Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {categories.map((category) => (
            <button
              key={category.id}
              onClick={() => setSelectedCategory(category.id)}
              className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                selectedCategory === category.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {category.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Connector Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {filteredConnectors.map((connector) => (
          <div
            key={connector.id}
            className="bg-white shadow rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => setSelectedConnector(connector)}
          >
            <div className="flex items-start">
              <connector.icon className="h-10 w-10 text-primary-600 flex-shrink-0" />
              <div className="ml-4 flex-1">
                <h3 className="text-lg font-medium text-gray-900">{connector.name}</h3>
                <p className="mt-1 text-sm text-gray-500">{connector.description}</p>
              </div>
            </div>
            <div className="mt-4 flex justify-end">
              <button className="btn btn-outline btn-sm">Configure</button>
            </div>
          </div>
        ))}
      </div>

      {/* Connected Sources */}
      <div className="mt-12">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Connected Sources</h2>
        <div className="bg-white shadow rounded-lg">
          <div className="p-6 text-center">
            <CloudIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No connected sources</h3>
            <p className="mt-1 text-sm text-gray-500">
              Select a connector above to start syncing data.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
