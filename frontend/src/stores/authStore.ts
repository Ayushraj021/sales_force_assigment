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
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const useAuthStore = create<AuthState & AuthActions>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
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
          set({
            user: {
              ...user,
              roles: user.roles.map((r: { name: string }) => r.name),
            },
            accessToken: token.accessToken,
            refreshToken: token.refreshToken,
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
          set({
            user: {
              ...user,
              roles: user.roles.map((r: { name: string }) => r.name),
            },
            accessToken: token.accessToken,
            refreshToken: token.refreshToken,
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
          set({
            accessToken: tokens.accessToken,
            refreshToken: tokens.refreshToken,
          })
        } catch (error) {
          // If refresh fails, logout
          get().logout()
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
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
