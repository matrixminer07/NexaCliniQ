import { ChartSkeleton } from '@/components/skeletons/ChartSkeleton'
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from 'recharts'

type DriftPoint = { day: string; [key: string]: number | string }

type DriftAlert = { id: string; feature_name: string; kl_divergence: number; detected_at: string; acknowledged_by?: string }

type DriftMonitorProps = {
  alerts: DriftAlert[]
  trend: DriftPoint[]
  loading: boolean
  error: string | null
  onAcknowledge: (id: string) => void
}

export function DriftMonitor({ alerts, trend, loading, error, onAcknowledge }: DriftMonitorProps) {
  if (loading) return <ChartSkeleton />
  if (error) return <div className="rounded-md border p-3 text-sm" style={{ borderColor: 'var(--color-border-tertiary)' }}>{error}</div>

  return (
    <div className="rounded-xl border p-4" style={{ background: 'var(--color-background-primary)', borderColor: 'var(--color-border-tertiary)' }}>
      <h3 className="text-base font-medium">Feature drift monitor</h3>
      <p className="mt-1 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
        D<sub>KL</sub>(P||Q) = sum P(x) log(P(x)/Q(x))
      </p>
      <div className="mt-4 h-[240px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={trend}>
            <CartesianGrid stroke="rgba(0,0,0,0.08)" />
            <XAxis dataKey="day" />
            <YAxis />
            <Tooltip />
            <Line dataKey="toxicity" stroke="var(--color-text-brand)" dot={false} />
            <Line dataKey="bioavailability" stroke="var(--color-text-success)" dot={false} />
            <Line dataKey="solubility" stroke="var(--color-text-warning)" dot={false} />
            <Line dataKey="binding" stroke="var(--color-text-secondary)" dot={false} />
            <Line dataKey="molecular_weight" stroke="var(--color-text-danger)" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 space-y-2">
        {alerts.map((alert) => (
          <div key={alert.id} className="flex items-center justify-between rounded-md border px-3 py-2" style={{ borderColor: 'var(--color-border-tertiary)' }}>
            <div className="text-sm">
              <span className="font-medium">{alert.feature_name}</span> KL={alert.kl_divergence.toFixed(6)} at {new Date(alert.detected_at).toLocaleString('en-IN')}
            </div>
            {alert.acknowledged_by ? (
              <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Ack: {alert.acknowledged_by}</span>
            ) : (
              <button type="button" className="btn-ghost" onClick={() => onAcknowledge(alert.id)}>Acknowledge</button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
