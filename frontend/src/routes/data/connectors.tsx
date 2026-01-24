import { createFileRoute, redirect } from '@tanstack/react-router'
import { DataConnectors } from '@/features/data/DataConnectors'
import { useAuthStore } from '@/stores/authStore'

export const Route = createFileRoute('/data/connectors')({
  beforeLoad: () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated
    if (!isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
  component: DataConnectors,
})
