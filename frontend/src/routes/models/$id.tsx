import { createFileRoute, redirect } from '@tanstack/react-router'
import { ModelDetail } from '@/features/models/ModelDetail'
import { useAuthStore } from '@/stores/authStore'

export const Route = createFileRoute('/models/$id')({
  beforeLoad: () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated
    if (!isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
  component: ModelDetail,
})
