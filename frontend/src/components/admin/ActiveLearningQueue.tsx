import { TableSkeleton } from '@/components/skeletons/TableSkeleton'
import { MathFormula } from '@/components/admin/MathFormula'

type QueueItem = {
  id: string
  compound_id: string
  predicted_probability: number
  entropy: number
  added_at: string
}

type ActiveLearningQueueProps = {
  items: QueueItem[]
  loading: boolean
  error: string | null
}

function entropyOfProbability(p: number) {
  const a = Math.max(1e-6, Math.min(1 - 1e-6, p))
  const b = 1 - a
  return -(a * Math.log2(a) + b * Math.log2(b))
}

export function ActiveLearningQueue({ items, loading, error }: ActiveLearningQueueProps) {
  if (loading) return <TableSkeleton rows={5} />
  if (error) return <div className="rounded-md border p-3 text-sm" style={{ borderColor: 'var(--color-border-tertiary)' }}>{error}</div>

  const labelledPct = items.length ? Math.round((items.filter((item) => item.entropy < 0.3).length / items.length) * 100) : 0

  return (
    <div className="rounded-xl border p-4" style={{ background: 'var(--color-background-primary)', borderColor: 'var(--color-border-tertiary)' }}>
      <h3 className="text-base font-medium">Active learning queue</h3>
      <MathFormula title="Model entropy" formula={'H = &minus;&sum; p(x) log<sub>2</sub> p(x)'} />
      <div className="mt-3">
        <div className="h-1 w-full overflow-hidden rounded" style={{ background: 'var(--color-background-secondary)' }}>
          <div className="h-full" style={{ width: `${labelledPct}%`, background: 'var(--color-text-brand)' }} />
        </div>
        <p className="mt-1 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
          {labelledPct}% labelled
        </p>
      </div>

      <table className="mt-3 w-full text-sm">
        <thead style={{ background: 'var(--color-background-secondary)' }}>
          <tr className="h-9 text-xs uppercase" style={{ letterSpacing: '0.05em', color: 'var(--color-text-secondary)' }}>
            <th className="px-3 text-left">Compound</th>
            <th className="px-3 text-left">Probability</th>
            <th className="px-3 text-left">Entropy</th>
            <th className="px-3 text-left">In queue</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const entropy = entropyOfProbability(item.predicted_probability)
            const entropyPct = Math.round(Math.min(1, entropy) * 100)
            return (
              <tr key={item.id} className="h-11 border-b" style={{ borderColor: 'var(--color-border-tertiary)' }}>
                <td className="px-3">{item.compound_id}</td>
                <td className="px-3">{item.predicted_probability.toFixed(4)}</td>
                <td className="px-3">
                  <div className="flex items-center gap-2">
                    <span>{entropy.toFixed(4)}</span>
                    <div className="h-1 w-20 overflow-hidden rounded" style={{ background: 'var(--color-background-secondary)' }}>
                      <div className="h-full" style={{ width: `${entropyPct}%`, background: 'var(--color-text-warning)' }} />
                    </div>
                  </div>
                </td>
                <td className="px-3">{new Date(item.added_at).toLocaleString('en-IN')}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
