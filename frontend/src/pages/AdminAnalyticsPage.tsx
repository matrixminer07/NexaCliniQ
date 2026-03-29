import { useCallback, useEffect, useMemo, useState } from 'react'
import { AdminPanelLayout } from '@/components/admin/AdminPanelLayout'
import { api, type AdminAnalyticsStats, type AdminModelAnalytics } from '@/services/api'

export function AdminAnalyticsPage() {
  const [stats, setStats] = useState<AdminAnalyticsStats | null>(null)
  const [models, setModels] = useState<AdminModelAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [statsPayload, modelPayload] = await Promise.all([api.adminAnalyticsStats(), api.adminAnalyticsModels()])
      setStats(statsPayload)
      setModels(modelPayload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics data.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const trend = useMemo(() => (stats?.daily_volume_7d ?? []).slice(-7), [stats])

  return (
    <AdminPanelLayout
      title="Admin Analytics"
      subtitle="Core performance metrics, drift alerts, and model telemetry."
      onRefresh={() => void refresh()}
      refreshing={loading}
    >
      {error ? <div className="rounded-md border border-red-400/40 bg-red-500/10 px-4 py-2 text-sm text-red-100">{error}</div> : null}

      <section className="grid md:grid-cols-4 gap-4">
        <div className="card-p">
          <p className="text-xs uppercase tracking-[0.12em] text-ink-tertiary">Predictions</p>
          <p className="text-2xl font-semibold mt-2">{stats?.total_predictions ?? 0}</p>
        </div>
        <div className="card-p">
          <p className="text-xs uppercase tracking-[0.12em] text-ink-tertiary">Pass Rate</p>
          <p className="text-2xl font-semibold mt-2">{stats?.pass_rate ?? 0}%</p>
        </div>
        <div className="card-p">
          <p className="text-xs uppercase tracking-[0.12em] text-ink-tertiary">Audit Anomalies (24h)</p>
          <p className="text-2xl font-semibold mt-2">{stats?.audit_anomalies_24h ?? 0}</p>
        </div>
        <div className="card-p">
          <p className="text-xs uppercase tracking-[0.12em] text-ink-tertiary">Drift Alerts (30d)</p>
          <p className="text-2xl font-semibold mt-2">{stats?.drift_alert_count_30d ?? 0}</p>
        </div>
      </section>

      <section className="grid md:grid-cols-2 gap-4">
        <div className="card-p">
          <h2 className="text-lg font-semibold mb-3">Daily Volume (7d)</h2>
          <div className="space-y-2">
            {trend.length ? trend.map((point) => (
              <div key={`${point.date}-${point.count}`} className="flex items-center justify-between text-sm border-b border-white/10 py-1">
                <span className="text-ink-secondary">{point.date}</span>
                <span className="font-semibold">{point.count}</span>
              </div>
            )) : <p className="text-sm text-ink-secondary">No daily trend data available.</p>}
          </div>
        </div>

        <div className="card-p">
          <h2 className="text-lg font-semibold mb-3">Model Summary</h2>
          <div className="space-y-2 text-sm">
            <p><span className="text-ink-secondary">Tracked Versions:</span> {models?.summary.versions_tracked ?? 0}</p>
            <p><span className="text-ink-secondary">Drift Alerts:</span> {models?.summary.drift_alert_count_30d ?? 0}</p>
            <p><span className="text-ink-secondary">Current Model:</span> {String(stats?.latest_model?.version ?? stats?.model_version ?? 'n/a')}</p>
          </div>
          <pre className="text-xs bg-black/20 rounded-md p-3 overflow-x-auto mt-3">{JSON.stringify(models?.latest ?? {}, null, 2)}</pre>
        </div>
      </section>

      <section className="card-p overflow-x-auto">
        <h2 className="text-lg font-semibold mb-3">Drift Alerts</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-ink-tertiary border-b border-white/10">
              <th className="py-2">Version</th>
              <th>Drift Score</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {(models?.drift_alerts ?? []).map((row, idx) => (
              <tr key={`${String(row.id ?? idx)}`} className="border-b border-white/5">
                <td className="py-2">{String(row.version ?? row.model_version ?? 'unknown')}</td>
                <td>{String(row.drift_score ?? row.score ?? '-')}</td>
                <td>{String(row.created_at ?? row.timestamp ?? '-')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </AdminPanelLayout>
  )
}
