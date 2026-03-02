import { createRootRoute, Link, Outlet, useNavigate, useRouterState } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/router-devtools'
import {
  HomeIcon,
  ChartBarIcon,
  CircleStackIcon,
  CubeIcon,
  DocumentChartBarIcon,
  Cog6ToothIcon,
  UserGroupIcon,
  BuildingOfficeIcon,
  ServerIcon,
  BeakerIcon,
} from '@heroicons/react/24/outline'
import { useAuthStore } from '@/stores/authStore'
import { useSessionManager } from '@/hooks/useSessionManager'
import { SessionTimeoutModal } from '@/components/SessionTimeoutModal'

// Routes that should not show the sidebar (public/auth pages)
const publicRoutes = ['/login', '/register', '/forgot-password', '/reset-password']

interface NavItem {
  name: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  adminOnly?: boolean
}

interface NavSection {
  title: string
  items: NavItem[]
}

const navigationSections: NavSection[] = [
  {
    title: 'Analytics',
    items: [
      { name: 'Dashboard', href: '/', icon: HomeIcon },
      { name: 'Forecasting', href: '/forecasting', icon: ChartBarIcon },
      { name: 'Reports', href: '/reports', icon: DocumentChartBarIcon },
    ],
  },
  {
    title: 'Data',
    items: [
      { name: 'Data Sources', href: '/data', icon: CircleStackIcon },
    ],
  },
  {
    title: 'Modeling',
    items: [
      { name: 'Models', href: '/models', icon: CubeIcon },
      { name: 'Experiments', href: '/experiments', icon: BeakerIcon },
    ],
  },
  {
    title: 'Administration',
    items: [
      { name: 'Users', href: '/admin/users', icon: UserGroupIcon, adminOnly: true },
      { name: 'Organization', href: '/settings/org', icon: BuildingOfficeIcon, adminOnly: true },
      { name: 'System Health', href: '/admin/system', icon: ServerIcon, adminOnly: true },
    ],
  },
]

function RootLayout() {
  const { user, isAuthenticated, logout } = useAuthStore()
  const navigate = useNavigate()
  const routerState = useRouterState()
  const currentPath = routerState.location.pathname

  // Session management
  const {
    showTimeoutWarning,
    timeRemaining,
    extendSession,
  } = useSessionManager()

  const handleLogout = () => {
    logout()
    navigate({ to: '/login' })
  }

  // Check if current route is a public route (no sidebar needed)
  const isPublicRoute = publicRoutes.some(route => currentPath.startsWith(route))

  // For public routes, render just the outlet without sidebar
  if (isPublicRoute || !isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Outlet />
        {import.meta.env.DEV && <TanStackRouterDevtools />}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200">
        {/* Logo */}
        <div className="flex items-center h-16 px-6 border-b border-gray-200">
          <ChartBarIcon className="h-8 w-8 text-primary-600" />
          <span className="ml-2 text-xl font-semibold text-gray-900">
            Sales Forecasting
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-4 space-y-6 overflow-y-auto">
          {navigationSections.map((section) => {
            const isAdmin = user?.roles?.includes('admin') || user?.isSuperuser
            const visibleItems = section.items.filter(
              (item) => !item.adminOnly || isAdmin
            )
            if (visibleItems.length === 0) return null

            return (
              <div key={section.title}>
                <h3 className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  {section.title}
                </h3>
                <div className="mt-2 space-y-1">
                  {visibleItems.map((item) => (
                    <Link
                      key={item.name}
                      to={item.href}
                      className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                      activeProps={{
                        className: 'bg-primary-50 text-primary-700',
                      }}
                    >
                      <item.icon className="mr-3 h-5 w-5" aria-hidden="true" />
                      {item.name}
                    </Link>
                  ))}
                </div>
              </div>
            )
          })}
        </nav>

        {/* User section */}
        <div className="border-t border-gray-200 p-4">
          <div>
            <Link
              to="/profile"
              className="flex items-center p-2 -mx-2 rounded-md hover:bg-gray-100"
            >
              <div className="flex-shrink-0">
                <div className="h-9 w-9 rounded-full bg-primary-600 flex items-center justify-center">
                  <span className="text-sm font-medium text-white">
                    {user?.firstName?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
                  </span>
                </div>
              </div>
              <div className="ml-3 flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {user?.fullName || user?.email}
                </p>
                <p className="text-xs text-gray-500 truncate">{user?.email}</p>
              </div>
            </Link>
            <div className="mt-3 flex items-center space-x-2">
              <Link
                to="/settings/account"
                className="flex-1 btn btn-outline btn-sm justify-center"
              >
                <Cog6ToothIcon className="h-4 w-4 mr-1" />
                Settings
              </Link>
              <button
                onClick={handleLogout}
                className="flex-1 btn btn-outline btn-sm justify-center text-red-600 hover:text-red-700 hover:bg-red-50"
              >
                Sign out
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="pl-64">
        {/* Header */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center px-6">
          <h1 className="text-lg font-semibold text-gray-900">
            Sales Forecasting & Marketing Mix Modeling
          </h1>
        </header>

        {/* Page content */}
        <main className="p-6">
          <Outlet />
        </main>
      </div>

      {/* Session timeout warning modal */}
      <SessionTimeoutModal
        isOpen={showTimeoutWarning}
        timeRemaining={timeRemaining}
        onExtend={extendSession}
        onLogout={handleLogout}
      />

      {/* Dev tools in development */}
      {import.meta.env.DEV && <TanStackRouterDevtools />}
    </div>
  )
}

export const Route = createRootRoute({
  component: RootLayout,
})
