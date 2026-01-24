import { createFileRoute, redirect } from '@tanstack/react-router'
import { DataSourceList } from '@/features/data/DataSourceList'
import { useAuthStore } from '@/stores/authStore'

export const Route = createFileRoute('/data/')({
  beforeLoad: () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated
    if (!isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
  component: DataSourceList,
})
