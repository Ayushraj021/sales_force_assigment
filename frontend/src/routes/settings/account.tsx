import { createFileRoute, redirect } from '@tanstack/react-router'
import { AccountSettings } from '@/features/settings/AccountSettings'
import { useAuthStore } from '@/stores/authStore'

export const Route = createFileRoute('/settings/account')({
  beforeLoad: () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated
    if (!isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
  component: AccountSettings,
})
