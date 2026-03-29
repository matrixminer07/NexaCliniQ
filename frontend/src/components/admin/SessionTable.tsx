import { TableSkeleton } from '@/components/skeletons/TableSkeleton'

type SessionItem = {
  token: string
  user: string
  email: string
  role: string
  created_at: string
  expires_at: string
  ip: string
}

type SessionTableProps = {
  sessions: SessionItem[]
  loading: boolean
  error: string | null
  onTerminate: (token: string) => Promise<void>
  onTerminateAll: () => Promise<void>
}

export function SessionTable({ sessions, loading, error, onTerminate, onTerminateAll }: SessionTableProps) {
  if (loading) return <TableSkeleton rows={5} />
  if (error) return <div className="rounded-md border p-3 text-sm" style={{ borderColor: 'var(--color-border-tertiary)' }}>{error}</div>

  return (
    <div className="rounded-xl border" style={{ background: 'var(--color-background-primary)', borderColor: 'var(--color-border-tertiary)' }}>
      <div className="flex items-center justify-between px-4 py-3">
        <h3 className="text-base font-medium">Active sessions</h3>
        <button type="button" className="btn-ghost" onClick={() => void onTerminateAll()}>Terminate all</button>
      </div>
      <table className="w-full text-sm">
        <thead style={{ background: 'var(--color-background-secondary)' }}>
          <tr className="h-9 text-xs uppercase" style={{ letterSpacing: '0.05em', color: 'var(--color-text-secondary)' }}>
            <th className="px-3 text-left">User</th>
            <th className="px-3 text-left">Email</th>
            <th className="px-3 text-left">Role</th>
            <th className="px-3 text-left">Created</th>
            <th className="px-3 text-left">Expires</th>
            <th className="px-3 text-left">IP</th>
            <th className="px-3 text-left">Actions</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((session) => (
            <tr key={session.token} className="h-11 border-b" style={{ borderColor: 'var(--color-border-tertiary)' }}>
              <td className="px-3">{session.user}</td>
              <td className="px-3">{session.email}</td>
              <td className="px-3">{session.role}</td>
              <td className="px-3">{new Date(session.created_at).toLocaleString('en-IN')}</td>
              <td className="px-3">{new Date(session.expires_at).toLocaleString('en-IN')}</td>
              <td className="px-3">{session.ip}</td>
              <td className="px-3">
                <button type="button" className="btn-ghost h-7 px-2" onClick={() => void onTerminate(session.token)}>
                  Terminate
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
