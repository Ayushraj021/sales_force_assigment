import { createFileRoute, redirect } from '@tanstack/react-router'
import { DataUpload } from '@/features/data/DataUpload'
import { useAuthStore } from '@/stores/authStore'

export const Route = createFileRoute('/data/upload')({
  beforeLoad: () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated
    if (!isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
  component: DataUpload,
})
