import { createFileRoute, redirect } from '@tanstack/react-router'
import { UserManagement } from '@/features/admin/UserManagement'
import { useAuthStore } from '@/stores/authStore'

export const Route = createFileRoute('/admin/users')({
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
  component: UserManagement,
})
