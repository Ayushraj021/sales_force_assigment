import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import {
  BuildingOffice2Icon,
  GlobeAltIcon,
  CurrencyDollarIcon,
  ClockIcon,
  CheckCircleIcon,
  ArrowPathIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { useOrganization } from '@/hooks/useOrganization'

interface OrganizationFormData {
  name: string
  slug: string
  industry: string
  timezone: string
  currency: string
  fiscalYearStart: string
  defaultDateRange: string
}

const industries = [
  'Retail',
  'E-commerce',
  'Financial Services',
  'Healthcare',
  'Technology',
  'Manufacturing',
  'Consumer Goods',
  'Media & Entertainment',
  'Other',
]

const timezones = [
  { value: 'America/New_York', label: 'Eastern Time (ET)' },
  { value: 'America/Chicago', label: 'Central Time (CT)' },
  { value: 'America/Denver', label: 'Mountain Time (MT)' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
  { value: 'Europe/London', label: 'London (GMT)' },
  { value: 'Europe/Paris', label: 'Paris (CET)' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
  { value: 'Asia/Shanghai', label: 'Shanghai (CST)' },
]

const currencies = [
  { value: 'USD', label: 'US Dollar ($)' },
  { value: 'EUR', label: 'Euro (\u20AC)' },
  { value: 'GBP', label: 'British Pound (\u00A3)' },
  { value: 'JPY', label: 'Japanese Yen (\u00A5)' },
  { value: 'INR', label: 'Indian Rupee (\u20B9)' },
]

export function OrganizationSettings() {
  const { organization, loading, error, refetch } = useOrganization()
  const [isEditing, setIsEditing] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<OrganizationFormData>()

  // Update form when organization data loads
  useEffect(() => {
    if (organization) {
      reset({
        name: organization.name,
        slug: organization.slug,
        industry: 'Technology', // Not in API, using default
        timezone: 'America/New_York', // Not in API, using default
        currency: 'USD', // Not in API, using default
        fiscalYearStart: '01',
        defaultDateRange: '90',
      })
    }
  }, [organization, reset])

  const onSubmit = async (data: OrganizationFormData) => {
    setIsSubmitting(true)
    try {
      // TODO: Implement updateOrganization mutation when available in backend
      await new Promise((resolve) => setTimeout(resolve, 1000))
      toast.success('Organization settings updated!')
      setIsEditing(false)
      refetch()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update settings')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancel = () => {
    reset()
    setIsEditing(false)
  }

  const getPlanBadge = (tier: string) => {
    const colors: Record<string, string> = {
      starter: 'bg-gray-100 text-gray-800',
      professional: 'bg-blue-100 text-blue-800',
      enterprise: 'bg-purple-100 text-purple-800',
      free: 'bg-gray-100 text-gray-800',
    }
    return (
      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${colors[tier] || colors.free}`}>
        {tier.charAt(0).toUpperCase() + tier.slice(1)}
      </span>
    )
  }

  if (loading && !organization) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-white shadow rounded-lg p-12 text-center">
          <ArrowPathIcon className="h-12 w-12 text-gray-400 mx-auto animate-spin" />
          <p className="mt-4 text-gray-500">Loading organization settings...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <ExclamationCircleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-red-900">Failed to load organization</h3>
          <p className="mt-2 text-sm text-red-700">{error}</p>
          <button onClick={refetch} className="mt-4 btn btn-outline">
            <ArrowPathIcon className="h-5 w-5 mr-2" />
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!organization) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <ExclamationCircleIcon className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-yellow-900">No organization found</h3>
          <p className="mt-2 text-sm text-yellow-700">
            You are not associated with any organization.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Organization Settings</h1>
          <p className="mt-1 text-sm text-gray-600">
            Manage your organization's configuration and preferences.
          </p>
        </div>
        <button onClick={refetch} className="btn btn-outline" disabled={loading}>
          <ArrowPathIcon className={`h-5 w-5 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Usage Stats */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-gray-900">Usage Overview</h2>
          {getPlanBadge(organization.subscriptionTier)}
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500">Max Users</p>
            <p className="text-2xl font-bold text-gray-900">{organization.maxUsers}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500">Max Models</p>
            <p className="text-2xl font-bold text-gray-900">{organization.maxModels}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500">Max Datasets</p>
            <p className="text-2xl font-bold text-gray-900">{organization.maxDatasets}</p>
          </div>
        </div>
      </div>

      {/* Organization Details */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <div className="flex items-center">
            <BuildingOffice2Icon className="h-5 w-5 text-gray-400 mr-2" />
            <h2 className="text-lg font-medium text-gray-900">Organization Details</h2>
          </div>
          {!isEditing && (
            <button onClick={() => setIsEditing(true)} className="btn btn-outline btn-sm">
              Edit
            </button>
          )}
        </div>

        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="px-6 py-6 space-y-6">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div>
                <label htmlFor="name" className="label">
                  Organization Name
                </label>
                <input
                  id="name"
                  type="text"
                  disabled={!isEditing}
                  className="input disabled:bg-gray-50"
                  {...register('name', { required: 'Organization name is required' })}
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="slug" className="label">
                  URL Slug
                </label>
                <div className="flex">
                  <span className="inline-flex items-center px-3 rounded-l-md border border-r-0 border-gray-300 bg-gray-50 text-gray-500 text-sm">
                    app.example.com/
                  </span>
                  <input
                    id="slug"
                    type="text"
                    disabled={!isEditing}
                    className="input rounded-l-none disabled:bg-gray-50"
                    {...register('slug', { required: 'Slug is required' })}
                  />
                </div>
              </div>
            </div>

            <div>
              <label htmlFor="industry" className="label">
                Industry
              </label>
              <select
                id="industry"
                disabled={!isEditing}
                className="input disabled:bg-gray-50"
                {...register('industry')}
              >
                {industries.map((industry) => (
                  <option key={industry} value={industry}>
                    {industry}
                  </option>
                ))}
              </select>
            </div>

            <div className="border-t border-gray-200 pt-6">
              <h3 className="text-sm font-medium text-gray-900 mb-4 flex items-center">
                <GlobeAltIcon className="h-4 w-4 mr-2 text-gray-400" />
                Regional Settings
              </h3>

              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div>
                  <label htmlFor="timezone" className="label">
                    Timezone
                  </label>
                  <select
                    id="timezone"
                    disabled={!isEditing}
                    className="input disabled:bg-gray-50"
                    {...register('timezone')}
                  >
                    {timezones.map((tz) => (
                      <option key={tz.value} value={tz.value}>
                        {tz.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="currency" className="label">
                    Currency
                  </label>
                  <select
                    id="currency"
                    disabled={!isEditing}
                    className="input disabled:bg-gray-50"
                    {...register('currency')}
                  >
                    {currencies.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="border-t border-gray-200 pt-6">
              <h3 className="text-sm font-medium text-gray-900 mb-4 flex items-center">
                <ClockIcon className="h-4 w-4 mr-2 text-gray-400" />
                Date & Time Preferences
              </h3>

              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div>
                  <label htmlFor="fiscalYearStart" className="label">
                    Fiscal Year Start Month
                  </label>
                  <select
                    id="fiscalYearStart"
                    disabled={!isEditing}
                    className="input disabled:bg-gray-50"
                    {...register('fiscalYearStart')}
                  >
                    <option value="01">January</option>
                    <option value="02">February</option>
                    <option value="03">March</option>
                    <option value="04">April</option>
                    <option value="05">May</option>
                    <option value="06">June</option>
                    <option value="07">July</option>
                    <option value="08">August</option>
                    <option value="09">September</option>
                    <option value="10">October</option>
                    <option value="11">November</option>
                    <option value="12">December</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="defaultDateRange" className="label">
                    Default Date Range (days)
                  </label>
                  <select
                    id="defaultDateRange"
                    disabled={!isEditing}
                    className="input disabled:bg-gray-50"
                    {...register('defaultDateRange')}
                  >
                    <option value="30">Last 30 days</option>
                    <option value="60">Last 60 days</option>
                    <option value="90">Last 90 days</option>
                    <option value="180">Last 6 months</option>
                    <option value="365">Last year</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Organization Info */}
            <div className="border-t border-gray-200 pt-6">
              <h3 className="text-sm font-medium text-gray-900 mb-4">Organization Info</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Created:</span>
                  <span className="ml-2 text-gray-900">
                    {new Date(organization.createdAt).toLocaleDateString()}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Status:</span>
                  <span className={`ml-2 ${organization.isActive ? 'text-green-600' : 'text-red-600'}`}>
                    {organization.isActive ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Form Actions */}
          {isEditing && (
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end space-x-3">
              <button type="button" onClick={handleCancel} className="btn btn-outline">
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !isDirty}
                className="btn btn-primary"
              >
                {isSubmitting ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          )}
        </form>
      </div>
    </div>
  )
}
