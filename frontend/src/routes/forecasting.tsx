import { createFileRoute, redirect } from '@tanstack/react-router'
import { ForecastGeneration } from '@/features/forecasting/ForecastGeneration'
import { useAuthStore } from '@/stores/authStore'

export const Route = createFileRoute('/forecasting')({
  beforeLoad: () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated
    if (!isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
  component: ForecastGeneration,
})
