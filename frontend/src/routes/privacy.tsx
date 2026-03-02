import { createFileRoute } from '@tanstack/react-router'
import { ConsentManagement } from '@/features/privacy/ConsentManagement'

export const Route = createFileRoute('/privacy')({
  component: ConsentManagement,
})
