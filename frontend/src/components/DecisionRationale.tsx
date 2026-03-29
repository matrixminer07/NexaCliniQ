import type { ShapBreakdown } from '@/types'

type DecisionRationaleProps = {
  shapBreakdown: ShapBreakdown
  score: number
}

function formatFeatureName(feature: string) {
  return feature.replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase())
}

export function DecisionRationale({ shapBreakdown, score }: DecisionRationaleProps) {
  const topContributions = [...shapBreakdown.contributions]
    .sort((a, b) => Math.abs(b.shap) - Math.abs(a.shap))
    .slice(0, 4)

  return (
    <section className="card-p space-y-3">
      <div className="text-sm text-ink-secondary">Decision Rationale</div>
      <div className="text-sm">
        Model score: <span className="font-semibold">{(score * 100).toFixed(1)}%</span>
      </div>

      <div className="space-y-2">
        {topContributions.map((item) => (
          <div key={`${item.feature}-${item.value}`} className="rounded-md bg-surface-1 px-3 py-2">
            <div className="flex items-center justify-between gap-2 text-sm">
              <span className="font-medium">{formatFeatureName(item.feature)}</span>
              <span className={item.shap >= 0 ? 'text-emerald-600' : 'text-red-600'}>
                {item.shap >= 0 ? '+' : ''}
                {item.shap.toFixed(3)}
              </span>
            </div>
            <div className="text-xs text-ink-secondary">Input value: {item.value.toFixed(3)}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
