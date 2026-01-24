import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  email: string
  firstName?: string
  lastName?: string
  fullName: string
  isActive: boolean
  isVerified: boolean
  isSuperuser: boolean
  organizationId?: string
  roles: string[]
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  tokenExpiresAt: number | null // Unix timestamp in milliseconds
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}

interface AuthActions {
  setUser: (user: User | null) => void
  setTokens: (accessToken: string, refreshToken: string) => void
  setLoading: (isLoading: boolean) => void
  setError: (error: string | null) => void
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, firstName?: string, lastName?: string) => Promise<void>
  logout: () => void
  refreshAccessToken: () => Promise<void>
  forgotPassword: (email: string) => Promise<void>
  resetPassword: (token: string, newPassword: string) => Promise<void>
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>
  updateProfile: (data: { firstName?: string; lastName?: string; email?: string }) => Promise<void>
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const useAuthStore = create<AuthState & AuthActions>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      tokenExpiresAt: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),

      login: async (email, password) => {
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${API_URL}/api/graphql`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              query: `
                mutation Login($input: LoginInput!) {
                  login(input: $input) {
                    token {
                      accessToken
                      refreshToken
                      expiresIn
                    }
                    user {
                      id
                      email
                      firstName
                      lastName
                      fullName
                      isActive
                      isVerified
                      isSuperuser
                      roles {
                        name
                      }
                    }
                  }
                }
              `,
              variables: {
                input: { email, password },
              },
            }),
          })

          const data = await response.json()

          if (data.errors) {
            throw new Error(data.errors[0].message)
          }

          const { token, user } = data.data.login
          // Calculate token expiration time (expiresIn is in seconds)
          const tokenExpiresAt = Date.now() + (token.expiresIn * 1000)
          set({
            user: {
              ...user,
              roles: user.roles.map((r: { name: string }) => r.name),
            },
            accessToken: token.accessToken,
            refreshToken: token.refreshToken,
            tokenExpiresAt,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Login failed',
            isLoading: false,
          })
          throw error
        }
      },

      register: async (email, password, firstName, lastName) => {
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${API_URL}/api/graphql`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              query: `
                mutation Register($input: RegisterInput!) {
                  register(input: $input) {
                    token {
                      accessToken
                      refreshToken
                      expiresIn
                    }
                    user {
                      id
                      email
                      firstName
                      lastName
                      fullName
                      isActive
                      isVerified
                      isSuperuser
                      roles {
                        name
                      }
                    }
                  }
                }
              `,
              variables: {
                input: { email, password, firstName, lastName },
              },
            }),
          })

          const data = await response.json()

          if (data.errors) {
            throw new Error(data.errors[0].message)
          }

          const { token, user } = data.data.register
          // Calculate token expiration time (expiresIn is in seconds)
          const tokenExpiresAt = Date.now() + (token.expiresIn * 1000)
          set({
            user: {
              ...user,
              roles: user.roles.map((r: { name: string }) => r.name),
            },
            accessToken: token.accessToken,
            refreshToken: token.refreshToken,
            tokenExpiresAt,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Registration failed',
            isLoading: false,
          })
          throw error
        }
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          tokenExpiresAt: null,
          isAuthenticated: false,
          error: null,
        })
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get()
        if (!refreshToken) {
          throw new Error('No refresh token available')
        }

        try {
          const response = await fetch(`${API_URL}/api/graphql`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              query: `
                mutation RefreshToken($refreshToken: String!) {
                  refreshToken(refreshToken: $refreshToken) {
                    accessToken
                    refreshToken
                    expiresIn
                  }
                }
              `,
              variables: { refreshToken },
            }),
          })

          const data = await response.json()

          if (data.errors) {
            throw new Error(data.errors[0].message)
          }

          const tokens = data.data.refreshToken
          // Calculate token expiration time (expiresIn is in seconds)
          const tokenExpiresAt = Date.now() + (tokens.expiresIn * 1000)
          set({
            accessToken: tokens.accessToken,
            refreshToken: tokens.refreshToken,
            tokenExpiresAt,
          })
        } catch (error) {
          // If refresh fails, logout
          get().logout()
          throw error
        }
      },

      forgotPassword: async (email) => {
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${API_URL}/api/graphql`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              query: `
                mutation ForgotPassword($email: String!) {
                  forgotPassword(email: $email) {
                    success
                    message
                  }
                }
              `,
              variables: { email },
            }),
          })

          const data = await response.json()

          if (data.errors) {
            throw new Error(data.errors[0].message)
          }

          set({ isLoading: false })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to send reset email',
            isLoading: false,
          })
          throw error
        }
      },

      resetPassword: async (token, newPassword) => {
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${API_URL}/api/graphql`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              query: `
                mutation ResetPassword($token: String!, $newPassword: String!) {
                  resetPassword(token: $token, newPassword: $newPassword) {
                    success
                    message
                  }
                }
              `,
              variables: { token, newPassword },
            }),
          })

          const data = await response.json()

          if (data.errors) {
            throw new Error(data.errors[0].message)
          }

          set({ isLoading: false })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to reset password',
            isLoading: false,
          })
          throw error
        }
      },

      changePassword: async (currentPassword, newPassword) => {
        const { accessToken } = get()
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${API_URL}/api/graphql`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${accessToken}`,
            },
            body: JSON.stringify({
              query: `
                mutation ChangePassword($input: ChangePasswordInput!) {
                  changePassword(input: $input) {
                    success
                    message
                  }
                }
              `,
              variables: {
                input: { currentPassword, newPassword },
              },
            }),
          })

          const data = await response.json()

          if (data.errors) {
            throw new Error(data.errors[0].message)
          }

          set({ isLoading: false })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to change password',
            isLoading: false,
          })
          throw error
        }
      },

      updateProfile: async (profileData) => {
        const { accessToken } = get()
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${API_URL}/api/graphql`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${accessToken}`,
            },
            body: JSON.stringify({
              query: `
                mutation UpdateProfile($input: UpdateProfileInput!) {
                  updateProfile(input: $input) {
                    id
                    email
                    firstName
                    lastName
                    fullName
                    isActive
                    isVerified
                    isSuperuser
                    roles {
                      name
                    }
                  }
                }
              `,
              variables: {
                input: profileData,
              },
            }),
          })

          const data = await response.json()

          if (data.errors) {
            throw new Error(data.errors[0].message)
          }

          const user = data.data.updateProfile
          set({
            user: {
              ...user,
              roles: user.roles.map((r: { name: string }) => r.name),
            },
            isLoading: false,
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to update profile',
            isLoading: false,
          })
          throw error
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        tokenExpiresAt: state.tokenExpiresAt,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
