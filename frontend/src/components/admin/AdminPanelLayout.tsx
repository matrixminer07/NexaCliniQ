import { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

type AdminPanelLayoutProps = {
  title: string
  subtitle: string
  children: ReactNode
  onRefresh?: () => void
  refreshing?: boolean
}

export function AdminPanelLayout({ title, subtitle, children, onRefresh, refreshing = false }: AdminPanelLayoutProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-surface-base text-ink-primary" data-theme="novacura">
      <main className="max-w-[1300px] mx-auto p-6 md:p-8 space-y-6">
        <section className="card-p flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold">{title}</h1>
            <p className="text-sm text-ink-secondary">{subtitle}</p>
            <p className="text-xs uppercase tracking-[0.18em] text-ink-tertiary mt-2">{user?.email ?? 'Admin user'}</p>
          </div>
          <div className="flex items-center gap-2">
            <button type="button" className="btn-ghost" onClick={() => navigate('/app')}>
              Workspace
            </button>
            {onRefresh ? (
              <button type="button" className="btn-ghost" onClick={onRefresh} disabled={refreshing}>
                {refreshing ? 'Refreshing...' : 'Refresh'}
              </button>
            ) : null}
            <button type="button" className="btn-ghost" onClick={() => void handleLogout()}>
              Logout
            </button>
          </div>
        </section>

        {children}
      </main>
    </div>
  )
}
