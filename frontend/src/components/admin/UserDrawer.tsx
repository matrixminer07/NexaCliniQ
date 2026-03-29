function timeAgo(ts: string) {
  const now = Date.now()
  const at = new Date(ts).getTime()
  const diff = Math.max(0, now - at)
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  if (diff < minute) return 'just now'
  if (diff < hour) return `${Math.floor(diff / minute)}m ago`
  if (diff < day) return `${Math.floor(diff / hour)}h ago`
  return `${Math.floor(diff / day)}d ago`
}

type UserDrawerProps = {
  user: Record<string, unknown>
  onClose: () => void
}

export function UserDrawer({ user, onClose }: UserDrawerProps) {
  const initials = String(user.name || user.email || 'NA')
    .split(' ')
    .map((v) => v[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <aside
      className="absolute right-0 top-0 z-10 h-full w-[400px] border-l p-6"
      style={{ background: 'var(--color-background-primary)', borderColor: 'var(--color-border-tertiary)' }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-full" style={{ background: 'var(--color-brand-soft)', color: 'var(--color-text-brand)' }}>
            {initials}
          </div>
          <div>
            <p className="font-medium" style={{ color: 'var(--color-text-primary)' }}>{String(user.name || 'Unknown')}</p>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>{String(user.email || '-')}</p>
          </div>
        </div>
        <button type="button" className="btn-ghost" onClick={onClose}>Close</button>
      </div>

      <div className="mt-6 space-y-2 text-sm">
        <p><strong>Role:</strong> {String(user.role || 'researcher')}</p>
        <p><strong>Status:</strong> {String(user.status || 'active')}</p>
        <p><strong>Joined:</strong> {user.created_at ? new Date(String(user.created_at)).toLocaleString('en-IN') : '-'}</p>
        <p><strong>Last login:</strong> {user.last_login ? timeAgo(String(user.last_login)) : 'never'}</p>
        <p><strong>Account ID:</strong> {String(user.id || '-')}</p>
      </div>
    </aside>
  )
}
