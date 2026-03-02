import { createFileRoute } from '@tanstack/react-router'
import { DataVersions } from '@/features/data/DataVersions'

export const Route = createFileRoute('/data/versions')({
  component: DataVersions,
})
