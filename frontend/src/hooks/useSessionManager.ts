import { useEffect, useRef, useCallback } from 'react'
import { useAuthStore } from '../stores/authStore'
import { authApi } from '../lib/api'
import toast from 'react-hot-toast'

/**
 * Session Manager Hook
 *
 * Handles:
 * 1. Activity tracking (mouse, keyboard, touch events)
 * 2. Heartbeat pings to keep session alive
 * 3. Inactivity detection and auto-logout
 */
export function useSessionManager() {
  const {
    isAuthenticated,
    sessionConfig,
    lastActivity,
    updateLastActivity,
    logout
  } = useAuthStore()

  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const inactivityCheckRef = useRef<NodeJS.Timeout | null>(null)
  const warningShownRef = useRef(false)

  // Handle user activity
  const handleActivity = useCallback(() => {
    if (isAuthenticated) {
      updateLastActivity()
      warningShownRef.current = false
    }
  }, [isAuthenticated, updateLastActivity])

  // Send heartbeat to server
  const sendHeartbeat = useCallback(async () => {
    if (!isAuthenticated) return

    try {
      await authApi.heartbeat()
    } catch (error: any) {
      // Check if session expired due to inactivity
      if (error.response?.status === 401) {
        const isInactivityExpiry = error.response?.headers?.['x-session-expired'] === 'inactivity'

        if (isInactivityExpiry) {
          toast.error('Session expired due to inactivity. Please login again.')
        }

        // Logout user
        logout()
        window.location.href = '/login'
      }
    }
  }, [isAuthenticated, logout])

  // Check for inactivity
  const checkInactivity = useCallback(() => {
    if (!isAuthenticated) return

    const now = Date.now()
    const inactiveTime = (now - lastActivity) / 1000  // in seconds
    const timeoutThreshold = sessionConfig.inactivityTimeout
    const warningThreshold = timeoutThreshold - 60  // Warn 60 seconds before timeout

    // Show warning 1 minute before timeout
    if (inactiveTime >= warningThreshold && !warningShownRef.current) {
      warningShownRef.current = true
      toast.error(
        `Session will expire in 1 minute due to inactivity. Move your mouse to stay logged in.`,
        { duration: 10000 }
      )
    }

    // Auto-logout if inactive for too long
    if (inactiveTime >= timeoutThreshold) {
      toast.error('Session expired due to inactivity.')
      logout()
      window.location.href = '/login'
    }
  }, [isAuthenticated, lastActivity, sessionConfig.inactivityTimeout, logout])

  // Set up event listeners for activity tracking
  useEffect(() => {
    if (!isAuthenticated) return

    const events = ['mousedown', 'mousemove', 'keydown', 'touchstart', 'scroll', 'click']

    // Throttle activity updates to prevent too many updates
    let throttleTimeout: NodeJS.Timeout | null = null
    const throttledActivityHandler = () => {
      if (!throttleTimeout) {
        throttleTimeout = setTimeout(() => {
          handleActivity()
          throttleTimeout = null
        }, 1000)  // Update at most once per second
      }
    }

    // Add event listeners
    events.forEach(event => {
      window.addEventListener(event, throttledActivityHandler, { passive: true })
    })

    return () => {
      events.forEach(event => {
        window.removeEventListener(event, throttledActivityHandler)
      })
      if (throttleTimeout) {
        clearTimeout(throttleTimeout)
      }
    }
  }, [isAuthenticated, handleActivity])

  // Set up heartbeat interval
  useEffect(() => {
    if (!isAuthenticated) {
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current)
        heartbeatIntervalRef.current = null
      }
      return
    }

    // Send heartbeat at configured interval
    heartbeatIntervalRef.current = setInterval(
      sendHeartbeat,
      sessionConfig.heartbeatInterval * 1000
    )

    // Send initial heartbeat
    sendHeartbeat()

    return () => {
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current)
        heartbeatIntervalRef.current = null
      }
    }
  }, [isAuthenticated, sessionConfig.heartbeatInterval, sendHeartbeat])

  // Set up inactivity check interval
  useEffect(() => {
    if (!isAuthenticated) {
      if (inactivityCheckRef.current) {
        clearInterval(inactivityCheckRef.current)
        inactivityCheckRef.current = null
      }
      return
    }

    // Check inactivity every 10 seconds
    inactivityCheckRef.current = setInterval(checkInactivity, 10000)

    return () => {
      if (inactivityCheckRef.current) {
        clearInterval(inactivityCheckRef.current)
        inactivityCheckRef.current = null
      }
    }
  }, [isAuthenticated, checkInactivity])

  return {
    isAuthenticated,
    sessionConfig,
    lastActivity,
  }
}
