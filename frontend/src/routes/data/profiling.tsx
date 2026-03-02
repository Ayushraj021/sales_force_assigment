import { createFileRoute } from '@tanstack/react-router'
import { DataProfilingDashboard } from '@/features/data/DataProfilingDashboard'

export const Route = createFileRoute('/data/profiling')({
  component: DataProfilingPage,
})

function DataProfilingPage() {
  return (
    <div className="p-6">
      <DataProfilingDashboard />
    </div>
  )
}
