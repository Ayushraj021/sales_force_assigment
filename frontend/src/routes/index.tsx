import { createFileRoute, redirect } from '@tanstack/react-router'
import { ExecutiveDashboard } from '@/features/dashboard/ExecutiveDashboard'
import { useAuthStore } from '@/stores/authStore'

export const Route = createFileRoute('/')({
  beforeLoad: () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated
    if (!isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
  component: HomePage,
})

function HomePage() {
  return <ExecutiveDashboard />
}
