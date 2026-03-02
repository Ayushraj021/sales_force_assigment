import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { UserCircleIcon, CameraIcon } from '@heroicons/react/24/outline'
import { useAuthStore } from '@/stores/authStore'
import toast from 'react-hot-toast'

interface ProfileFormData {
  firstName: string
  lastName: string
  email: string
}

export function ProfilePage() {
  const [isEditing, setIsEditing] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { user, updateProfile } = useAuthStore()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<ProfileFormData>({
    defaultValues: {
      firstName: user?.firstName || '',
      lastName: user?.lastName || '',
      email: user?.email || '',
    },
  })

  const onSubmit = async (data: ProfileFormData) => {
    setIsSubmitting(true)
    try {
      await updateProfile({
        firstName: data.firstName,
        lastName: data.lastName,
      })
      toast.success('Profile updated successfully!')
      setIsEditing(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to update profile')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancel = () => {
    reset()
    setIsEditing(false)
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Profile</h1>
        <p className="mt-1 text-sm text-gray-600">
          Manage your account information and preferences.
        </p>
      </div>

      <div className="bg-white shadow rounded-lg">
        {/* Profile Header */}
        <div className="px-6 py-8 border-b border-gray-200">
          <div className="flex items-center">
            <div className="relative">
              <div className="h-24 w-24 rounded-full bg-primary-100 flex items-center justify-center">
                {user?.firstName ? (
                  <span className="text-3xl font-medium text-primary-700">
                    {user.firstName[0]}{user.lastName?.[0] || ''}
                  </span>
                ) : (
                  <UserCircleIcon className="h-16 w-16 text-primary-600" />
                )}
              </div>
              <button
                type="button"
                className="absolute bottom-0 right-0 h-8 w-8 rounded-full bg-white shadow-md flex items-center justify-center border border-gray-200 hover:bg-gray-50"
              >
                <CameraIcon className="h-4 w-4 text-gray-500" />
              </button>
            </div>
            <div className="ml-6">
              <h2 className="text-xl font-semibold text-gray-900">
                {user?.fullName || user?.email}
              </h2>
              <p className="text-sm text-gray-500">{user?.email}</p>
              <div className="mt-2 flex items-center space-x-2">
                {user?.isVerified ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Verified
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                    Unverified
                  </span>
                )}
                {user?.roles?.map((role) => (
                  <span
                    key={role}
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800"
                  >
                    {role}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Profile Form */}
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="px-6 py-6 space-y-6">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div>
                <label htmlFor="firstName" className="label">
                  First name
                </label>
                <input
                  id="firstName"
                  type="text"
                  disabled={!isEditing}
                  className="input disabled:bg-gray-50 disabled:text-gray-500"
                  {...register('firstName', {
                    required: 'First name is required',
                  })}
                />
                {errors.firstName && (
                  <p className="mt-1 text-sm text-red-600">{errors.firstName.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="lastName" className="label">
                  Last name
                </label>
                <input
                  id="lastName"
                  type="text"
                  disabled={!isEditing}
                  className="input disabled:bg-gray-50 disabled:text-gray-500"
                  {...register('lastName', {
                    required: 'Last name is required',
                  })}
                />
                {errors.lastName && (
                  <p className="mt-1 text-sm text-red-600">{errors.lastName.message}</p>
                )}
              </div>
            </div>

            <div>
              <label htmlFor="email" className="label">
                Email address
              </label>
              <input
                id="email"
                type="email"
                disabled
                className="input disabled:bg-gray-50 disabled:text-gray-500"
                {...register('email')}
              />
              <p className="mt-1 text-sm text-gray-500">
                Email address cannot be changed. Contact support if you need to update it.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div>
                <label className="label">Organization</label>
                <p className="text-sm text-gray-900">
                  {user?.organizationId || 'Not assigned'}
                </p>
              </div>

              <div>
                <label className="label">Account Status</label>
                <p className="text-sm text-gray-900">
                  {user?.isActive ? 'Active' : 'Inactive'}
                </p>
              </div>
            </div>
          </div>

          {/* Form Actions */}
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end space-x-3">
            {isEditing ? (
              <>
                <button
                  type="button"
                  onClick={handleCancel}
                  className="btn btn-outline"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !isDirty}
                  className="btn btn-primary"
                >
                  {isSubmitting ? 'Saving...' : 'Save changes'}
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="btn btn-primary"
              >
                Edit profile
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Quick Links */}
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <a
          href="/settings/account"
          className="bg-white shadow rounded-lg p-6 hover:shadow-md transition-shadow"
        >
          <h3 className="text-lg font-medium text-gray-900">Account Settings</h3>
          <p className="mt-1 text-sm text-gray-500">
            Change password, security settings, and preferences
          </p>
        </a>
        <a
          href="/settings"
          className="bg-white shadow rounded-lg p-6 hover:shadow-md transition-shadow"
        >
          <h3 className="text-lg font-medium text-gray-900">Branding Settings</h3>
          <p className="mt-1 text-sm text-gray-500">
            Customize the look and feel of your dashboard
          </p>
        </a>
      </div>
    </div>
  )
}
