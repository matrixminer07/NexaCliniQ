import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

export interface TabShellProps {
  isLoading?: boolean
  error?: string | null
  is401?: boolean
  onRetry?: () => void
  children: React.ReactNode
}

export function TabShell({ isLoading = false, error = null, is401 = false, onRetry, children }: TabShellProps) {
  const navigate = useNavigate()
  const { logout } = useAuth()

  useEffect(() => {
    if (!is401) return
    let cancelled = false
    const run = async () => {
      await logout()
      if (!cancelled) {
        navigate('/login', { replace: true })
      }
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [is401, logout, navigate])

  if (isLoading) {
    return (
      <div className="space-y-3 animate-pulse" aria-live="polite" aria-busy="true">
        <div className="h-12 rounded border border-line bg-surface-2" />
        <div className="h-24 rounded border border-line bg-surface-2" />
        <div className="h-24 rounded border border-line bg-surface-2" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded border border-line bg-surface-1 p-4 space-y-3">
        <p className="text-sm font-medium text-ink-primary">Unable to load this module.</p>
        <p className="text-xs text-ink-secondary">{error}</p>
        {onRetry ? (
          <button type="button" onClick={onRetry} className="rounded border border-line px-3 py-1.5 text-xs hover:bg-surface-2">
            Retry
          </button>
        ) : null}
      </div>
    )
  }

  return <>{children}</>
}
