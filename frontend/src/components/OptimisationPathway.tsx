import type { CounterfactualResponse, FeatureSet } from '@/types'
import { useAppStore } from '@/store'

interface OptimisationPathwayProps {
  counterfactual: CounterfactualResponse | null
  baselineProb: number
}

export function OptimisationPathway({ counterfactual, baselineProb }: OptimisationPathwayProps) {
  const setFeatureA = useAppStore((s) => s.setFeatureA)

  const changes = counterfactual?.changes_required ?? []
  const tiers = [changes.slice(0, 1), changes.slice(0, 2), changes]

  const applyTier = (tierIndex: number) => {
    for (const change of tiers[tierIndex]) {
      setFeatureA(change.feature as keyof FeatureSet, change.suggested)
    }
  }

  return (
    <div className="card-p space-y-3">
      <h3 className="font-display text-lg">Optimisation Pathway</h3>
      {tiers.map((tier, i) => {
        const gain = tier.reduce((sum, c) => sum + Math.abs(c.delta) * 0.12, 0)
        const projected = Math.min(0.95, baselineProb + gain)
        return (
          <div key={i} className="rounded-xl border border-[rgba(0,200,150,0.15)] p-3 space-y-2">
            <div className="text-sm text-ink-secondary">Option {i + 1}</div>
            <div className="h-2 bg-surface-1 rounded overflow-hidden"><div className="h-full bg-brand" style={{ width: `${projected * 100}%`, transition: 'width 400ms ease-out' }} /></div>
            <div className="text-xs text-ink-secondary font-mono">{(baselineProb * 100).toFixed(1)}% to {(projected * 100).toFixed(1)}%</div>
            <button className="btn-ghost" onClick={() => applyTier(i)}>Apply</button>
          </div>
        )
      })}
    </div>
  )
}
