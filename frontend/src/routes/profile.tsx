import { createFileRoute, redirect } from '@tanstack/react-router'
import { ProfilePage } from '@/features/profile/ProfilePage'
import { useAuthStore } from '@/stores/authStore'

export const Route = createFileRoute('/profile')({
  beforeLoad: () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated
    if (!isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
  component: ProfilePage,
})
