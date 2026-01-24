import { GraphQLClient } from 'graphql-request'
import { useAuthStore } from '@/stores/authStore'

const API_URL = import.meta.env.VITE_GRAPHQL_URL || 'http://localhost:8000/api/graphql'

function getAuthHeaders(): Record<string, string> {
  const accessToken = useAuthStore.getState().accessToken
  if (accessToken) {
    return {
      Authorization: `Bearer ${accessToken}`,
    }
  }
  return {}
}

export const graphqlClient = new GraphQLClient(API_URL, {
  headers: getAuthHeaders,
})

// Helper function to create a client with current auth state
export function createAuthenticatedClient(): GraphQLClient {
  const accessToken = useAuthStore.getState().accessToken
  return new GraphQLClient(API_URL, {
    headers: accessToken
      ? {
          Authorization: `Bearer ${accessToken}`,
        }
      : {},
  })
}

// Generic fetch function with error handling
export async function gqlRequest<T>(
  query: string,
  variables?: Record<string, unknown>
): Promise<T> {
  try {
    const client = createAuthenticatedClient()
    return await client.request<T>(query, variables)
  } catch (error: unknown) {
    // Check if it's an auth error and try to refresh token
    if (
      error &&
      typeof error === 'object' &&
      'response' in error
    ) {
      const gqlError = error as { response?: { errors?: Array<{ message: string }> } }
      if (
        gqlError.response?.errors?.some(
          (e) =>
            e.message.includes('not authenticated') ||
            e.message.includes('Invalid token')
        )
      ) {
        // Try to refresh the token
        try {
          await useAuthStore.getState().refreshAccessToken()
          // Retry the request
          const client = createAuthenticatedClient()
          return await client.request<T>(query, variables)
        } catch {
          // Refresh failed, logout
          useAuthStore.getState().logout()
        }
      }
    }
    throw error
  }
}
