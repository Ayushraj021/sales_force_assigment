/**
 * Session Manager Hook
 *
 * Handles automatic session refresh and idle timeout warnings.
 * - Auto-refreshes token when user is active and token is about to expire
 * - Shows warning modal when user is idle and session is about to expire
 * - Allows user to extend session or logout
 */

import { useEffect, useRef, useCallback, useState } from 'react'
import { useAuthStore } from '@/stores/authStore'

// Configuration
const SESSION_WARNING_TIME = 2 * 60 * 1000 // Show warning 2 minutes before expiry
const IDLE_TIMEOUT = 5 * 60 * 1000 // Consider user idle after 5 minutes of inactivity
const REFRESH_BUFFER = 5 * 60 * 1000 // Refresh token 5 minutes before expiry
const ACTIVITY_EVENTS = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click']

interface SessionManagerState {
  showTimeoutWarning: boolean
  timeRemaining: number // seconds
  isIdle: boolean
}

interface SessionManagerActions {
  extendSession: () => Promise<void>
  dismissWarning: () => void
}

export function useSessionManager(): SessionManagerState & SessionManagerActions {
  const {
    isAuthenticated,
    tokenExpiresAt,
    refreshAccessToken,
    logout
  } = useAuthStore()

  const [showTimeoutWarning, setShowTimeoutWarning] = useState(false)
  const [timeRemaining, setTimeRemaining] = useState(0)
  const [isIdle, setIsIdle] = useState(false)

  const lastActivityRef = useRef<number>(Date.now())
  const warningTimerRef = useRef<NodeJS.Timeout | null>(null)
  const countdownTimerRef = useRef<NodeJS.Timeout | null>(null)
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null)
  const idleTimerRef = useRef<NodeJS.Timeout | null>(null)

  // Update last activity timestamp
  const updateActivity = useCallback(() => {
    lastActivityRef.current = Date.now()
    setIsIdle(false)

    // Reset idle timer
    if (idleTimerRef.current) {
      clearTimeout(idleTimerRef.current)
    }
    idleTimerRef.current = setTimeout(() => {
      setIsIdle(true)
    }, IDLE_TIMEOUT)
  }, [])

  // Extend session by refreshing token
  const extendSession = useCallback(async () => {
    try {
      await refreshAccessToken()
      setShowTimeoutWarning(false)
      setTimeRemaining(0)
      updateActivity()
    } catch (error) {
      console.error('Failed to extend session:', error)
      logout()
    }
  }, [refreshAccessToken, logout, updateActivity])

  // Dismiss warning (user chose to stay logged in)
  const dismissWarning = useCallback(() => {
    setShowTimeoutWarning(false)
    extendSession()
  }, [extendSession])

  // Clear all timers
  const clearAllTimers = useCallback(() => {
    if (warningTimerRef.current) clearTimeout(warningTimerRef.current)
    if (countdownTimerRef.current) clearInterval(countdownTimerRef.current)
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
    if (idleTimerRef.current) clearTimeout(idleTimerRef.current)
  }, [])

  // Set up session management
  useEffect(() => {
    if (!isAuthenticated || !tokenExpiresAt) {
      clearAllTimers()
      setShowTimeoutWarning(false)
      return
    }

    const now = Date.now()
    const timeUntilExpiry = tokenExpiresAt - now

    // If token is already expired, logout
    if (timeUntilExpiry <= 0) {
      logout()
      return
    }

    // Schedule auto-refresh when user is active
    const timeUntilRefresh = timeUntilExpiry - REFRESH_BUFFER
    if (timeUntilRefresh > 0) {
      refreshTimerRef.current = setTimeout(() => {
        // Only auto-refresh if user is active
        if (!isIdle) {
          refreshAccessToken().catch((error) => {
            console.error('Auto-refresh failed:', error)
          })
        }
      }, timeUntilRefresh)
    }

    // Schedule warning when user is idle
    const timeUntilWarning = timeUntilExpiry - SESSION_WARNING_TIME
    if (timeUntilWarning > 0) {
      warningTimerRef.current = setTimeout(() => {
        // Only show warning if user is idle
        const timeSinceActivity = Date.now() - lastActivityRef.current
        if (timeSinceActivity >= IDLE_TIMEOUT) {
          setShowTimeoutWarning(true)
          setTimeRemaining(Math.ceil(SESSION_WARNING_TIME / 1000))

          // Start countdown
          countdownTimerRef.current = setInterval(() => {
            setTimeRemaining((prev) => {
              if (prev <= 1) {
                clearInterval(countdownTimerRef.current!)
                logout()
                return 0
              }
              return prev - 1
            })
          }, 1000)
        } else {
          // User is active, try to refresh
          refreshAccessToken().catch((error) => {
            console.error('Refresh failed:', error)
          })
        }
      }, timeUntilWarning)
    } else if (timeUntilExpiry > 0 && timeUntilExpiry <= SESSION_WARNING_TIME) {
      // Already within warning window
      const timeSinceActivity = Date.now() - lastActivityRef.current
      if (timeSinceActivity >= IDLE_TIMEOUT) {
        setShowTimeoutWarning(true)
        setTimeRemaining(Math.ceil(timeUntilExpiry / 1000))

        countdownTimerRef.current = setInterval(() => {
          setTimeRemaining((prev) => {
            if (prev <= 1) {
              clearInterval(countdownTimerRef.current!)
              logout()
              return 0
            }
            return prev - 1
          })
        }, 1000)
      }
    }

    return () => {
      clearAllTimers()
    }
  }, [isAuthenticated, tokenExpiresAt, isIdle, refreshAccessToken, logout, clearAllTimers])

  // Track user activity
  useEffect(() => {
    if (!isAuthenticated) return

    // Initial activity
    updateActivity()

    // Add event listeners
    ACTIVITY_EVENTS.forEach((event) => {
      window.addEventListener(event, updateActivity, { passive: true })
    })

    return () => {
      ACTIVITY_EVENTS.forEach((event) => {
        window.removeEventListener(event, updateActivity)
      })
    }
  }, [isAuthenticated, updateActivity])

  // If user becomes active while warning is showing, extend session
  useEffect(() => {
    if (showTimeoutWarning && !isIdle) {
      extendSession()
    }
  }, [showTimeoutWarning, isIdle, extendSession])

  return {
    showTimeoutWarning,
    timeRemaining,
    isIdle,
    extendSession,
    dismissWarning,
  }
}
