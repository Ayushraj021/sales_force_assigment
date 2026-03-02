import { createFileRoute, redirect } from '@tanstack/react-router'
import { SystemHealth } from '@/features/admin/SystemHealth'
import { useAuthStore } from '@/stores/authStore'

export const Route = createFileRoute('/admin/system')({
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
  component: SystemHealth,
})
