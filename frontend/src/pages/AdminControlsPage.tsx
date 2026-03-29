import { useCallback, useEffect, useState } from 'react'
import { AdminPanelLayout } from '@/components/admin/AdminPanelLayout'
import { api, type AdminControlApproval, type AdminFeatureFlag } from '@/services/api'

export function AdminControlsPage() {
  const [approvals, setApprovals] = useState<AdminControlApproval[]>([])
  const [flags, setFlags] = useState<AdminFeatureFlag[]>([])
  const [models, setModels] = useState<Array<Record<string, unknown>>>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [approvalPayload, flagPayload, modelPayload] = await Promise.all([
        api.adminControlsApprovals(),
        api.adminControlsFeatureFlags(),
        api.adminControlsModels(20),
      ])
      setApprovals(approvalPayload.items)
      setFlags(flagPayload.items)
      setModels(modelPayload.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load controls panel.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

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
      setFlags((prev) => prev.map((item) => (item.key === updated.key ? updated : item)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update feature flag.')
    }
  }

  async function rollbackModel(version: string) {
    try {
      await api.adminControlsRollback(version, 'Rollback initiated from admin controls panel')
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Rollback request failed.')
    }
  }

  return (
    <AdminPanelLayout
      title="Admin Controls"
      subtitle="Operational controls for approvals, feature flags, and model rollbacks."
      onRefresh={() => void refresh()}
      refreshing={loading}
    >
      {error ? <div className="rounded-md border border-red-400/40 bg-red-500/10 px-4 py-2 text-sm text-red-100">{error}</div> : null}

      <section className="grid md:grid-cols-3 gap-4">
        <div className="card-p">
          <p className="text-xs uppercase tracking-[0.12em] text-ink-tertiary">Pending Approvals</p>
          <p className="text-2xl font-semibold mt-2">{approvals.filter((item) => item.status === 'pending').length}</p>
        </div>
        <div className="card-p">
          <p className="text-xs uppercase tracking-[0.12em] text-ink-tertiary">Feature Flags</p>
          <p className="text-2xl font-semibold mt-2">{flags.length}</p>
        </div>
        <div className="card-p">
          <p className="text-xs uppercase tracking-[0.12em] text-ink-tertiary">Rollback Candidates</p>
          <p className="text-2xl font-semibold mt-2">{models.length}</p>
        </div>
      </section>

      <section className="card-p overflow-x-auto">
        <h2 className="text-lg font-semibold mb-3">Approvals</h2>
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
      </section>

      <section className="card-p overflow-x-auto">
        <h2 className="text-lg font-semibold mb-3">Feature Flags</h2>
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
            {flags.map((flag) => (
              <tr key={flag.key} className="border-b border-white/5">
                <td className="py-2 font-mono">{flag.key}</td>
                <td>{flag.description ?? '-'}</td>
                <td>{flag.enabled ? 'true' : 'false'}</td>
                <td>
                  <button type="button" className="btn-ghost" onClick={() => void toggleFlag(flag)}>
                    Toggle
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card-p overflow-x-auto">
        <h2 className="text-lg font-semibold mb-3">Model Rollbacks</h2>
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
            {models.map((row, idx) => {
              const version = String(row.version ?? row.id ?? `candidate-${idx}`)
              return (
                <tr key={`${version}-${idx}`} className="border-b border-white/5">
                  <td className="py-2">{version}</td>
                  <td>{String(row.val_auc ?? row.cv_auc_mean ?? '-')}</td>
                  <td className="font-mono text-xs">{String(row.artifact_path ?? '-')}</td>
                  <td>
                    <button type="button" className="btn-ghost" onClick={() => void rollbackModel(version)}>
                      Rollback
                    </button>
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
