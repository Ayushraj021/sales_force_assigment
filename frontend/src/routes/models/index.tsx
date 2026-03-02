import { createFileRoute, redirect } from '@tanstack/react-router'
import { ModelList } from '@/features/models/ModelList'
import { useAuthStore } from '@/stores/authStore'

export const Route = createFileRoute('/models/')({
  beforeLoad: () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated
    if (!isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
  component: ModelList,
})
