import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  email: string
  name: string
  role: string
  organization_id?: string
  is_active?: boolean
  is_verified?: boolean
}

interface SessionConfig {
  inactivityTimeout: number  // in seconds
  heartbeatInterval: number  // in seconds
}

interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  sessionConfig: SessionConfig
  lastActivity: number  // timestamp
  login: (token: string, refreshToken: string, user: User, sessionConfig?: SessionConfig) => void
  logout: () => void
  updateUser: (user: Partial<User>) => void
  updateLastActivity: () => void
  setSessionConfig: (config: SessionConfig) => void
}

const DEFAULT_SESSION_CONFIG: SessionConfig = {
  inactivityTimeout: 300,  // 5 minutes default
  heartbeatInterval: 30,   // 30 seconds default
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      sessionConfig: DEFAULT_SESSION_CONFIG,
      lastActivity: Date.now(),

      login: (token: string, refreshToken: string, user: User, sessionConfig?: SessionConfig) => {
        set({
          token,
          refreshToken,
          user,
          isAuthenticated: true,
          sessionConfig: sessionConfig || DEFAULT_SESSION_CONFIG,
          lastActivity: Date.now(),
        })
      },

      logout: () => {
        set({
          token: null,
          refreshToken: null,
          user: null,
          isAuthenticated: false,
          sessionConfig: DEFAULT_SESSION_CONFIG,
          lastActivity: 0,
        })
      },

      updateUser: (userData: Partial<User>) => {
        set((state) => ({
          user: state.user ? { ...state.user, ...userData } : null,
        }))
      },

      updateLastActivity: () => {
        set({ lastActivity: Date.now() })
      },

      setSessionConfig: (config: SessionConfig) => {
        set({ sessionConfig: config })
      },
    }),
    {
      name: 'dpdp-auth-storage',
    }
  )
)
