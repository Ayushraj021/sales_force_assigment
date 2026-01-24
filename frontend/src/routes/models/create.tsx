import { createFileRoute, redirect } from '@tanstack/react-router'
import { ModelCreationWizard } from '@/features/models/ModelCreationWizard'
import { useAuthStore } from '@/stores/authStore'

export const Route = createFileRoute('/models/create')({
  beforeLoad: () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated
    if (!isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
  component: ModelCreationWizard,
})
