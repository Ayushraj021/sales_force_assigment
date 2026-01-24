import { createFileRoute, redirect } from '@tanstack/react-router'
import { ReportBuilder } from '@/features/reports/ReportBuilder'
import { useAuthStore } from '@/stores/authStore'

export const Route = createFileRoute('/reports')({
  beforeLoad: () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated
    if (!isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
  component: ReportBuilder,
})
