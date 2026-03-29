import { memo, useMemo } from 'react'
import type { ShapBreakdown } from '@/types'
import { GlossaryTooltip } from '@/components/GlossaryTooltip'

interface SHAPWaterfallProps {
  breakdown: ShapBreakdown
}

export const SHAPWaterfall = memo(function SHAPWaterfall({ breakdown }: SHAPWaterfallProps) {
  const sorted = useMemo(() => {
    const positive = breakdown.contributions.filter((c) => c.shap >= 0)
    const negative = breakdown.contributions.filter((c) => c.shap < 0)
    return { positive, negative }
  }, [breakdown.contributions])

  const maxAbs = Math.max(...breakdown.contributions.map((c) => Math.abs(c.shap)), 0.01)

  const renderBar = (feature: string, shap: number, direction: 'positive' | 'negative') => {
    const width = `${(Math.abs(shap) / maxAbs) * 100}%`
    return (
      <div key={`${feature}-${direction}`} className="space-y-1">
        <div className="flex justify-between text-xs">
          <span className="text-ink-secondary"><GlossaryTooltip term="SHAP">{feature}</GlossaryTooltip></span>
          <span className="font-mono text-ink-primary">{shap >= 0 ? '+' : ''}{(shap * 100).toFixed(1)}pp</span>
        </div>
        <div className="h-2 bg-surface-1 rounded overflow-hidden">
          <div className={`h-2 ${direction === 'positive' ? 'bg-brand' : 'bg-state-fail'}`} style={{ width }} />
        </div>
      </div>
    )
  }

  return (
    <div className="card-p space-y-4">
      <h3 className="font-display text-lg"><GlossaryTooltip term="SHAP">SHAP Waterfall</GlossaryTooltip></h3>
      <div className="space-y-2">
        <div className="label">Strengths</div>
        {sorted.positive.map((c) => renderBar(c.feature, c.shap, 'positive'))}
      </div>
      <div className="divider" />
      <div className="space-y-2">
        <div className="label">Opportunities to improve</div>
        {sorted.negative.map((c) => renderBar(c.feature, c.shap, 'negative'))}
      </div>
      <div className="text-xs text-ink-tertiary font-mono">Base {breakdown.base_value.toFixed(2)} to final {breakdown.final_prediction.toFixed(2)}</div>
    </div>
  )
})
