/**
 * Session Timeout Warning Modal
 *
 * Displays a modal when the user's session is about to expire.
 * Shows countdown timer and allows user to extend session or logout.
 */

import { Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { ExclamationTriangleIcon, ClockIcon } from '@heroicons/react/24/outline'
import { useAuthStore } from '@/stores/authStore'

interface SessionTimeoutModalProps {
  isOpen: boolean
  timeRemaining: number // seconds
  onExtend: () => void
  onLogout: () => void
}

export function SessionTimeoutModal({
  isOpen,
  timeRemaining,
  onExtend,
  onLogout,
}: SessionTimeoutModalProps) {
  const logout = useAuthStore((state) => state.logout)

  const handleLogout = () => {
    logout()
    onLogout()
  }

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-[100]" onClose={() => {}}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                <div className="flex items-center justify-center mb-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-yellow-100">
                    <ExclamationTriangleIcon className="h-6 w-6 text-yellow-600" aria-hidden="true" />
                  </div>
                </div>

                <Dialog.Title
                  as="h3"
                  className="text-lg font-semibold leading-6 text-gray-900 text-center"
                >
                  Session Expiring Soon
                </Dialog.Title>

                <div className="mt-4">
                  <p className="text-sm text-gray-500 text-center">
                    Your session will expire due to inactivity. Would you like to stay logged in?
                  </p>

                  {/* Countdown Timer */}
                  <div className="mt-6 flex flex-col items-center">
                    <div className="flex items-center justify-center space-x-2 text-gray-600">
                      <ClockIcon className="h-5 w-5" />
                      <span className="text-sm">Time remaining:</span>
                    </div>
                    <div className="mt-2 text-4xl font-bold text-red-600 tabular-nums">
                      {formatTime(timeRemaining)}
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="mt-4 h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-red-500 transition-all duration-1000 ease-linear"
                      style={{ width: `${(timeRemaining / 120) * 100}%` }}
                    />
                  </div>
                </div>

                <div className="mt-6 flex flex-col sm:flex-row gap-3">
                  <button
                    type="button"
                    className="flex-1 inline-flex justify-center rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 transition-colors"
                    onClick={onExtend}
                  >
                    Stay Logged In
                  </button>
                  <button
                    type="button"
                    className="flex-1 inline-flex justify-center rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors"
                    onClick={handleLogout}
                  >
                    Log Out
                  </button>
                </div>

                <p className="mt-4 text-xs text-gray-400 text-center">
                  You will be automatically logged out when the timer reaches zero.
                </p>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
