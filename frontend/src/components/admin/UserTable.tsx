import { useMemo, useState } from 'react'
import { TableSkeleton } from '@/components/skeletons/TableSkeleton'
import { UserDrawer } from '@/components/admin/UserDrawer'

type UserItem = {
  id: string
  name: string
  email: string
  role: 'admin' | 'researcher' | 'viewer'
  status?: 'active' | 'suspended'
  mfa_enabled?: boolean
  last_login?: string | null
  created_at?: string
  predictions_run?: number
}

type UserTableProps = {
  users: UserItem[]
  total: number
  loading: boolean
  error: string | null
  page: number
  setPage: (next: number) => void
  onUpdateRole: (id: string, role: UserItem['role']) => Promise<void>
  onForceLogout: (id: string) => Promise<void>
  onToggleSuspend: (id: string, suspended: boolean) => Promise<void>
}

const PAGE_SIZE = 20

export function UserTable({ users, total, loading, error, page, setPage, onUpdateRole, onForceLogout, onToggleSuspend }: UserTableProps) {
  const [editingRoleUser, setEditingRoleUser] = useState<string | null>(null)
  const [nextRole, setNextRole] = useState<UserItem['role']>('viewer')
  const [selectedUser, setSelectedUser] = useState<UserItem | null>(null)

  const showingLabel = useMemo(() => {
    if (!total) return 'Showing 0-0 of 0 users'
    const start = (page - 1) * PAGE_SIZE + 1
    const end = Math.min(page * PAGE_SIZE, total)
    return `Showing ${start}-${end} of ${total} users`
  }, [page, total])

  if (loading) return <TableSkeleton rows={8} />
  if (error) return <div className="rounded-md border p-3 text-sm" style={{ borderColor: 'var(--color-border-tertiary)' }}>{error}</div>

  return (
    <div className="relative rounded-xl border" style={{ background: 'var(--color-background-primary)', borderColor: 'var(--color-border-tertiary)' }}>
      <div className="flex items-center justify-between px-4 py-3">
        <h3 className="text-base font-medium">All users</h3>
        <button type="button" className="btn-ghost">Export CSV</button>
      </div>
      <table className="w-full text-sm">
        <thead style={{ background: 'var(--color-background-secondary)' }}>
          <tr className="h-9 text-xs uppercase" style={{ letterSpacing: '0.05em', color: 'var(--color-text-secondary)' }}>
            <th className="px-3 text-left">Name</th>
            <th className="px-3 text-left">Email</th>
            <th className="px-3 text-left">Role</th>
            <th className="px-3 text-left">Status</th>
            <th className="px-3 text-left">MFA</th>
            <th className="px-3 text-left">Last login</th>
            <th className="px-3 text-left">Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id} className="h-11 border-b" style={{ borderColor: 'var(--color-border-tertiary)' }}>
              <td className="px-3">
                <button type="button" className="text-left hover:underline" onClick={() => setSelectedUser(user)}>{user.name || 'Unknown'}</button>
              </td>
              <td className="px-3">{user.email}</td>
              <td className="px-3">{user.role}</td>
              <td className="px-3">{user.status || 'active'}</td>
              <td className="px-3">{user.mfa_enabled ? 'Yes' : 'No'}</td>
              <td className="px-3">{user.last_login ? new Date(user.last_login).toLocaleString('en-IN') : 'never'}</td>
              <td className="px-3 space-x-2">
                {editingRoleUser === user.id ? (
                  <>
                    <select value={nextRole} onChange={(e) => setNextRole(e.target.value as UserItem['role'])} className="input h-8">
                      <option value="admin">admin</option>
                      <option value="researcher">researcher</option>
                      <option value="viewer">viewer</option>
                    </select>
                    <button type="button" className="btn-ghost" onClick={() => void onUpdateRole(user.id, nextRole)}>Save</button>
                    <button type="button" className="btn-ghost" onClick={() => setEditingRoleUser(null)}>Cancel</button>
                  </>
                ) : (
                  <>
                    <button type="button" className="btn-ghost h-7 px-2" onClick={() => { setEditingRoleUser(user.id); setNextRole(user.role) }}>Edit</button>
                    <button type="button" className="btn-ghost h-7 px-2" onClick={() => void onForceLogout(user.id)}>Logout</button>
                    <button type="button" className="btn-ghost h-7 px-2" onClick={() => void onToggleSuspend(user.id, user.status !== 'suspended')}>
                      {user.status === 'suspended' ? 'Unsuspend' : 'Suspend'}
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex items-center justify-between px-4 py-3 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
        <span>{showingLabel}</span>
        <div className="space-x-2">
          <button type="button" className="btn-ghost" disabled={page <= 1} onClick={() => setPage(Math.max(1, page - 1))}>Previous</button>
          <button type="button" className="btn-ghost" disabled={page * PAGE_SIZE >= total} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      </div>

      {selectedUser ? <UserDrawer user={selectedUser} onClose={() => setSelectedUser(null)} /> : null}
    </div>
  )
}
