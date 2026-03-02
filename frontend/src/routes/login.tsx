import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { LoginForm } from '@/features/auth/LoginForm'

export const Route = createFileRoute('/login')({
  component: LoginPage,
})

function LoginPage() {
  const navigate = useNavigate()

  const handleSuccess = () => {
    navigate({ to: '/' })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full">
        <LoginForm onSuccess={handleSuccess} />
      </div>
    </div>
  )
}
