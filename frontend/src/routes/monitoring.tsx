import { createFileRoute } from '@tanstack/react-router'
import { MonitoringDashboard } from '@/features/monitoring/MonitoringDashboard'

export const Route = createFileRoute('/monitoring')({
  component: MonitoringDashboard,
})
