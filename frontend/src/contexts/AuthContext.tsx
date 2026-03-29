import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '@/services/api'
import { AuthUser, clearAuthSession, getAuthToken, getAuthenticatedUser, setAccessToken, setAuthSession } from '@/auth'

type AuthContextValue = {
  user: AuthUser | null
  token: string | null
  isAuthenticated: boolean
  loading: boolean
  login: (nextToken: string, nextUser: AuthUser) => void
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => getAuthenticatedUser())
  const [token, setToken] = useState<string | null>(() => getAuthToken())
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true

    async function rehydrate() {
      try {
        const refreshed = await api.refreshAccessToken()
        setAccessToken(refreshed.access_token)
        const me = await api.me()
        if (!mounted) return
        const nextUser: AuthUser = {
          id: me.id,
          email: me.email,
          name: me.name,
          picture: me.picture,
          role: me.role,
        }
        setAuthSession(refreshed.access_token, nextUser)
        setUser(nextUser)
        setToken(refreshed.access_token)
      } catch {
        if (!mounted) return
        clearAuthSession()
        setUser(null)
        setToken(null)
      } finally {
        if (mounted) setLoading(false)
      }
    }

    void rehydrate()

    return () => {
      mounted = false
    }
  }, [])

  function login(nextToken: string, nextUser: AuthUser) {
    setAuthSession(nextToken, nextUser)
    setUser(nextUser)
    setToken(nextToken)
  }

  async function logout() {
    try {
      await api.logout()
    } catch {
      // Ignore remote logout errors and clear local session anyway.
    } finally {
      clearAuthSession()
      setUser(null)
      setToken(null)
    }
  }

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isAuthenticated: Boolean(token),
      loading,
      login,
      logout,
    }),
    [user, token, loading]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
