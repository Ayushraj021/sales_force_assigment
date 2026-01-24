import { createFileRoute } from '@tanstack/react-router'
import { JobScheduler } from '@/features/scheduler/JobScheduler'

export const Route = createFileRoute('/scheduler')({
  component: JobScheduler,
})
