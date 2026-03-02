import { createFileRoute, redirect } from '@tanstack/react-router'
import { OrganizationSettings } from '@/features/admin/OrganizationSettings'
import { useAuthStore } from '@/stores/authStore'

export const Route = createFileRoute('/settings/org')({
  beforeLoad: () => {
    const { isAuthenticated, user } = useAuthStore.getState()
    if (!isAuthenticated) {
      throw redirect({ to: '/login' })
    }
    // Only allow admins
    if (!user?.roles.includes('admin') && !user?.isSuperuser) {
      throw redirect({ to: '/' })
    }
  },
  component: OrganizationSettings,
})
