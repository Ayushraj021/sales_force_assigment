import { createFileRoute } from '@tanstack/react-router'
import { ExecutiveDashboard } from '@/features/dashboard/ExecutiveDashboard'

export const Route = createFileRoute('/')({
  component: HomePage,
})

function HomePage() {
  return <ExecutiveDashboard />
}
