import { createFileRoute, redirect } from '@tanstack/react-router'
import { GeoLiftExperiment } from '@/features/experiments'
import { useAuthStore } from '@/stores/authStore'

export const Route = createFileRoute('/experiments')({
  beforeLoad: () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated
    if (!isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
  component: ExperimentsPage,
})

function ExperimentsPage() {
  return <GeoLiftExperiment />
}
