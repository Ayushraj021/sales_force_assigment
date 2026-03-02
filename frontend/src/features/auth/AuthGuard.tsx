import { useNavigate } from '@tanstack/react-router'
import { useEffect } from 'react'
import { useAuthStore } from '@/stores/authStore'

interface AuthGuardProps {
  children: React.ReactNode
  requireAuth?: boolean
  requiredRoles?: string[]
}

export function AuthGuard({
  children,
  requireAuth = true,
  requiredRoles = [],
}: AuthGuardProps) {
  const navigate = useNavigate()
  const { isAuthenticated, user } = useAuthStore()

  useEffect(() => {
    if (requireAuth && !isAuthenticated) {
      navigate({ to: '/login' })
      return
    }

    if (requiredRoles.length > 0 && user) {
      const hasRequiredRole = requiredRoles.some((role) =>
        user.roles.includes(role)
      )
      if (!hasRequiredRole) {
        navigate({ to: '/' })
      }
    }
  }, [isAuthenticated, user, requireAuth, requiredRoles, navigate])

  if (requireAuth && !isAuthenticated) {
    return null
  }

  if (requiredRoles.length > 0 && user) {
    const hasRequiredRole = requiredRoles.some((role) =>
      user.roles.includes(role)
    )
    if (!hasRequiredRole) {
      return null
    }
  }

  return <>{children}</>
}
