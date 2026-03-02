import { createFileRoute } from '@tanstack/react-router'
import { ETLPipelineManager } from '@/features/etl/ETLPipelineManager'

export const Route = createFileRoute('/etl')({
  component: ETLPipelineManager,
})
