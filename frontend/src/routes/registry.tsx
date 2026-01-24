import { createFileRoute } from '@tanstack/react-router'
import { ModelRegistry } from '@/features/registry/ModelRegistry'

export const Route = createFileRoute('/registry')({
  component: ModelRegistry,
})
