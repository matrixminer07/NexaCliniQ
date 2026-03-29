import { useCallback, useEffect, useMemo, useState } from 'react'
import { AdminPanelLayout } from '@/components/admin/AdminPanelLayout'
import { api, type AdminAnalyticsStats, type AdminControlApproval, type AdminFeatureFlag, type AdminModelAnalytics } from '@/services/api'

type AdminUser = {
  id: string
  email: string
  name: string
  role: 'admin' | 'researcher' | 'viewer'
  mfa_enabled?: boolean
  created_at?: string
  last_login?: string | null
}

type AuditLog = {
  id: string
  timestamp: string
  method: string
  path: string
  status: number
  request_id?: string | null
}

type UserRoleFilter = 'admin' | 'researcher' | 'viewer' | 'all'

export function AdminDashboardPage() {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [audit, setAudit] = useState<AuditLog[]>([])
  const [stats, setStats] = useState<AdminAnalyticsStats | null>(null)
  const [modelAnalytics, setModelAnalytics] = useState<AdminModelAnalytics | null>(null)
  const [approvals, setApprovals] = useState<AdminControlApproval[]>([])
  const [featureFlags, setFeatureFlags] = useState<AdminFeatureFlag[]>([])
  const [rollbackCandidates, setRollbackCandidates] = useState<Array<Record<string, unknown>>>([])
  const [error, setError] = useState<string>('')
  const [usersLoading, setUsersLoading] = useState(true)
  const [auditLoading, setAuditLoading] = useState(true)
  const [analyticsLoading, setAnalyticsLoading] = useState(true)
  const [controlsLoading, setControlsLoading] = useState(true)
  const [userQuery, setUserQuery] = useState<{ limit: number; offset: number; role: UserRoleFilter; search: string }>({
    limit: 25,
    offset: 0,
    role: 'all',
    search: '',
  })
  const [usersMeta, setUsersMeta] = useState({ limit: 25, offset: 0, total: 0 })
  const [auditQuery, setAuditQuery] = useState({ limit: 50, offset: 0, method: 'all', status: 'all', path: '', requestId: '' })
  const [auditMeta, setAuditMeta] = useState({ limit: 50, offset: 0, total: 0 })

  const fetchUsers = useCallback(async () => {
    setUsersLoading(true)
    setError('')
    try {
      const payload = await api.adminListUsers(userQuery)
      setUsers(payload.items)
      setUsersMeta({ limit: payload.limit, offset: payload.offset, total: payload.total })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users.')
    } finally {
      setUsersLoading(false)
    }
  }, [userQuery])

  const fetchAudit = useCallback(async () => {
    setAuditLoading(true)
    setError('')
    try {
      const payload = await api.adminAuditLogs({
        ...auditQuery,
        method: auditQuery.method,
        status: auditQuery.status,
        path: auditQuery.path,
        requestId: auditQuery.requestId,
      })
      setAudit(payload.items)
      setAuditMeta({ limit: payload.limit, offset: payload.offset, total: payload.total })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit logs.')
    } finally {
      setAuditLoading(false)
    }
  }, [auditQuery])

  const fetchAnalytics = useCallback(async () => {
    setAnalyticsLoading(true)
    setError('')
    try {
      const [statsPayload, modelsPayload] = await Promise.all([api.adminAnalyticsStats(), api.adminAnalyticsModels()])
      setStats(statsPayload)
      setModelAnalytics(modelsPayload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics.')
    } finally {
      setAnalyticsLoading(false)
    }
  }, [])

  const fetchControls = useCallback(async () => {
    setControlsLoading(true)
    setError('')
    try {
      const [approvalsPayload, flagsPayload, modelsPayload] = await Promise.all([
        api.adminControlsApprovals(),
        api.adminControlsFeatureFlags(),
        api.adminControlsModels(20),
      ])
      setApprovals(approvalsPayload.items)
      setFeatureFlags(flagsPayload.items)
      setRollbackCandidates(modelsPayload.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load controls.')
    } finally {
      setControlsLoading(false)
    }
  }, [])

  const refreshAll = useCallback(async () => {
    await Promise.all([fetchUsers(), fetchAudit(), fetchAnalytics(), fetchControls()])
  }, [fetchUsers, fetchAudit, fetchAnalytics, fetchControls])

  useEffect(() => {
    void fetchUsers()
  }, [fetchUsers])

  useEffect(() => {
    void fetchAudit()
  }, [fetchAudit])

  useEffect(() => {
    void fetchAnalytics()
  }, [fetchAnalytics])

  useEffect(() => {
    void fetchControls()
  }, [fetchControls])

  const adminCount = useMemo(() => users.filter((u) => u.role === 'admin').length, [users])

  const userRangeText = useMemo(() => {
    if (!users.length) {
      return 'Showing 0 of 0'
    }
    const start = userQuery.offset + 1
    const end = Math.min(userQuery.offset + users.length, usersMeta.total || userQuery.offset + users.length)
    const total = usersMeta.total || users.length
    return `Showing ${start}-${end} of ${total}`
  }, [users.length, userQuery.offset, usersMeta.total])

  const auditRangeText = useMemo(() => {
    if (!audit.length) {
      return 'Showing 0 of 0'
    }
    const start = auditQuery.offset + 1
    const end = Math.min(auditQuery.offset + audit.length, auditMeta.total || auditQuery.offset + audit.length)
    const total = auditMeta.total || audit.length
    return `Showing ${start}-${end} of ${total}`
  }, [audit.length, auditQuery.offset, auditMeta.total])

  async function updateRole(userId: string, role: AdminUser['role']) {
    try {
      const updated = await api.adminUpdateUserRole(userId, role)
      setUsers((prev) => prev.map((item) => (item.id === updated.id ? { ...item, role: updated.role } : item)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update role.')
    }
  }

  async function decideApproval(approvalId: string, decision: 'approved' | 'rejected') {
    try {
      const updated = await api.adminControlsDecision(approvalId, decision)
      setApprovals((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update approval.')
    }
  }

  async function toggleFlag(flag: AdminFeatureFlag) {
    try {
      const updated = await api.adminControlsUpdateFeatureFlag(flag.key, { enabled: !flag.enabled })
      setFeatureFlags((prev) => prev.map((item) => (item.key === updated.key ? updated : item)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update feature flag.')
    }
  }

  async function rollbackModel(version: string) {
    try {
      await api.adminControlsRollback(version, 'Rollback initiated from admin control center')
      await fetchControls()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rollback model.')
    }
  }

  return (
    <AdminPanelLayout
      title="Admin Dashboard"
      subtitle="Unified admin control center for users, analytics, and governance controls."
      onRefresh={() => void refreshAll()}
      refreshing={usersLoading || auditLoading || analyticsLoading || controlsLoading}
    >
      {error ? <div className="rounded-md border border-red-400/40 bg-red-500/10 px-4 py-2 text-sm text-red-100">{error}</div> : null}

      <section className="grid md:grid-cols-3 gap-4">
        <div className="card-p">
          <p className="text-xs uppercase tracking-[0.12em] text-ink-tertiary">Users</p>
          <p className="mt-2 text-2xl font-semibold">{usersMeta.total || users.length}</p>
        </div>
        <div className="card-p">
          <p className="text-xs uppercase tracking-[0.12em] text-ink-tertiary">Admins</p>
          <p className="mt-2 text-2xl font-semibold">{adminCount}</p>
        </div>
        <div className="card-p">
          <p className="text-xs uppercase tracking-[0.12em] text-ink-tertiary">Audit Events</p>
          <p className="mt-2 text-2xl font-semibold">{auditMeta.total || audit.length}</p>
        </div>
        <div className="card-p">
          <p className="text-xs uppercase tracking-[0.12em] text-ink-tertiary">Predictions</p>
          <p className="mt-2 text-2xl font-semibold">{stats?.total_predictions ?? 0}</p>
        </div>
        <div className="card-p">
          <p className="text-xs uppercase tracking-[0.12em] text-ink-tertiary">Drift Alerts (30d)</p>
          <p className="mt-2 text-2xl font-semibold">{stats?.drift_alert_count_30d ?? 0}</p>
        </div>
        <div className="card-p">
          <p className="text-xs uppercase tracking-[0.12em] text-ink-tertiary">Pending Approvals</p>
          <p className="mt-2 text-2xl font-semibold">{approvals.filter((item) => item.status === 'pending').length}</p>
        </div>
      </section>

      <section className="card-p overflow-x-auto">
        <h2 className="text-lg font-semibold mb-3">User Access</h2>
        <div className="flex flex-wrap gap-3 items-end mb-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-ink-tertiary uppercase tracking-[0.2em]">Search</label>
            <input
              className="input h-9"
              placeholder="Email or name"
              value={userQuery.search}
              onChange={(e) => setUserQuery((prev) => ({ ...prev, search: e.target.value, offset: 0 }))}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-ink-tertiary uppercase tracking-[0.2em]">Role</label>
            <select
              className="input h-9"
              value={userQuery.role}
              onChange={(e) => setUserQuery((prev) => ({ ...prev, role: e.target.value as UserRoleFilter, offset: 0 }))}
            >
              <option value="all">All roles</option>
              <option value="viewer">Viewer</option>
              <option value="researcher">Researcher</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div className="flex items-center gap-2 ml-auto">
            <button
              type="button"
              className="btn-ghost"
              disabled={userQuery.offset === 0 || usersLoading}
              onClick={() => setUserQuery((prev) => ({ ...prev, offset: Math.max(0, prev.offset - prev.limit) }))}
            >
              Previous
            </button>
            <button
              type="button"
              className="btn-ghost"
              disabled={usersLoading || userQuery.offset + usersMeta.limit >= (usersMeta.total || usersMeta.limit)}
              onClick={() => setUserQuery((prev) => ({ ...prev, offset: prev.offset + prev.limit }))}
            >
              Next
            </button>
          </div>
        </div>
        <p className="text-xs text-ink-secondary mb-2">{userRangeText}</p>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-ink-tertiary border-b border-white/10">
              <th className="py-2">Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>MFA</th>
              <th>Last login</th>
            </tr>
          </thead>
          <tbody>
            {users.map((entry) => (
              <tr key={entry.id} className="border-b border-white/5">
                <td className="py-2">{entry.name || 'Unknown'}</td>
                <td>{entry.email}</td>
                <td>
                  <select
                    className="input h-8"
                    value={entry.role}
                    onChange={(e) => void updateRole(entry.id, e.target.value as AdminUser['role'])}
                  >
                    <option value="viewer">viewer</option>
                    <option value="researcher">researcher</option>
                    <option value="admin">admin</option>
                  </select>
                </td>
                <td>{entry.mfa_enabled ? 'enabled' : 'disabled'}</td>
                <td>{entry.last_login ? new Date(entry.last_login).toLocaleString() : 'never'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {usersLoading ? <p className="text-xs text-ink-tertiary mt-2">Loading users...</p> : null}
      </section>

      <section className="card-p overflow-x-auto">
        <h2 className="text-lg font-semibold mb-3">Audit Logs</h2>
        <div className="flex flex-wrap gap-3 items-end mb-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-ink-tertiary uppercase tracking-[0.2em]">Method</label>
            <select
              className="input h-9"
              value={auditQuery.method}
              onChange={(e) => setAuditQuery((prev) => ({ ...prev, method: e.target.value, offset: 0 }))}
            >
              <option value="all">All</option>
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
              <option value="PATCH">PATCH</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-ink-tertiary uppercase tracking-[0.2em]">Status</label>
            <input
              className="input h-9"
              type="number"
              placeholder="e.g. 403"
              value={auditQuery.status === 'all' ? '' : auditQuery.status}
              onChange={(e) => {
                const value = e.target.value
                setAuditQuery((prev) => ({ ...prev, status: value || 'all', offset: 0 }))
              }}
            />
          </div>
          <div className="flex flex-col gap-1 flex-1 min-w-[180px]">
            <label className="text-xs text-ink-tertiary uppercase tracking-[0.2em]">Path contains</label>
            <input
              className="input h-9"
              placeholder="/predict"
              value={auditQuery.path}
              onChange={(e) => setAuditQuery((prev) => ({ ...prev, path: e.target.value, offset: 0 }))}
            />
          </div>
          <div className="flex flex-col gap-1 flex-1 min-w-[160px]">
            <label className="text-xs text-ink-tertiary uppercase tracking-[0.2em]">Request ID</label>
            <input
              className="input h-9"
              placeholder="UUID"
              value={auditQuery.requestId}
              onChange={(e) => setAuditQuery((prev) => ({ ...prev, requestId: e.target.value, offset: 0 }))}
            />
          </div>
          <div className="flex items-center gap-2 ml-auto">
            <button
              type="button"
              className="btn-ghost"
              disabled={auditQuery.offset === 0 || auditLoading}
              onClick={() => setAuditQuery((prev) => ({ ...prev, offset: Math.max(0, prev.offset - prev.limit) }))}
            >
              Previous
            </button>
            <button
              type="button"
              className="btn-ghost"
              disabled={auditLoading || auditQuery.offset + auditMeta.limit >= (auditMeta.total || auditMeta.limit)}
              onClick={() => setAuditQuery((prev) => ({ ...prev, offset: prev.offset + prev.limit }))}
            >
              Next
            </button>
          </div>
        </div>
        <p className="text-xs text-ink-secondary mb-2">{auditRangeText}</p>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-ink-tertiary border-b border-white/10">
              <th className="py-2">Time</th>
              <th>Method</th>
              <th>Path</th>
              <th>Status</th>
              <th>Request ID</th>
            </tr>
          </thead>
          <tbody>
            {audit.map((entry) => (
              <tr key={entry.id} className="border-b border-white/5">
                <td className="py-2">{new Date(entry.timestamp).toLocaleString()}</td>
                <td>{entry.method}</td>
                <td>{entry.path}</td>
                <td>{entry.status}</td>
                <td className="font-mono text-xs">{entry.request_id || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {auditLoading ? <p className="text-xs text-ink-tertiary mt-2">Loading audit logs...</p> : null}
      </section>

      <section className="card-p overflow-x-auto">
        <h2 className="text-lg font-semibold mb-3">Analytics: Drift Alerts</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-ink-tertiary border-b border-white/10">
              <th className="py-2">Version</th>
              <th>Drift Score</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {(modelAnalytics?.drift_alerts ?? []).map((row, idx) => (
              <tr key={`${String(row.id ?? idx)}`} className="border-b border-white/5">
                <td className="py-2">{String(row.version ?? row.model_version ?? 'unknown')}</td>
                <td>{String(row.drift_score ?? row.score ?? '-')}</td>
                <td>{String(row.created_at ?? row.timestamp ?? '-')}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {analyticsLoading ? <p className="text-xs text-ink-tertiary mt-2">Loading analytics...</p> : null}
      </section>

      <section className="card-p overflow-x-auto">
        <h2 className="text-lg font-semibold mb-3">Controls: Approvals</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-ink-tertiary border-b border-white/10">
              <th className="py-2">Request</th>
              <th>Category</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {approvals.map((item) => (
              <tr key={item.id} className="border-b border-white/5">
                <td className="py-2">{item.title}</td>
                <td>{item.category}</td>
                <td>{item.status}</td>
                <td className="space-x-2">
                  <button type="button" className="btn-ghost" disabled={item.status !== 'pending'} onClick={() => void decideApproval(item.id, 'approved')}>Approve</button>
                  <button type="button" className="btn-ghost" disabled={item.status !== 'pending'} onClick={() => void decideApproval(item.id, 'rejected')}>Reject</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {controlsLoading ? <p className="text-xs text-ink-tertiary mt-2">Loading controls...</p> : null}
      </section>

      <section className="card-p overflow-x-auto">
        <h2 className="text-lg font-semibold mb-3">Controls: Feature Flags</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-ink-tertiary border-b border-white/10">
              <th className="py-2">Flag</th>
              <th>Description</th>
              <th>Enabled</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {featureFlags.map((flag) => (
              <tr key={flag.key} className="border-b border-white/5">
                <td className="py-2 font-mono">{flag.key}</td>
                <td>{flag.description ?? '-'}</td>
                <td>{flag.enabled ? 'true' : 'false'}</td>
                <td>
                  <button type="button" className="btn-ghost" onClick={() => void toggleFlag(flag)}>Toggle</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card-p overflow-x-auto">
        <h2 className="text-lg font-semibold mb-3">Controls: Model Rollbacks</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-ink-tertiary border-b border-white/10">
              <th className="py-2">Version</th>
              <th>AUC</th>
              <th>Path</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {rollbackCandidates.map((row, idx) => {
              const version = String(row.version ?? row.id ?? `candidate-${idx}`)
              return (
                <tr key={`${version}-${idx}`} className="border-b border-white/5">
                  <td className="py-2">{version}</td>
                  <td>{String(row.val_auc ?? row.cv_auc_mean ?? '-')}</td>
                  <td className="font-mono text-xs">{String(row.artifact_path ?? '-')}</td>
                  <td>
                    <button type="button" className="btn-ghost" onClick={() => void rollbackModel(version)}>Rollback</button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </section>
    </AdminPanelLayout>
  )
}
