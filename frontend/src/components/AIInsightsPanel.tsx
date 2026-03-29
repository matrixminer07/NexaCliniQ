import type { CounterfactualResponse, PredictionResponse } from '@/types'
import { useInsights } from '@/hooks/useInsights'
import { DNALoader } from './DNALoader'

interface AIInsightsPanelProps {
  prediction: PredictionResponse | null
  counterfactual: CounterfactualResponse | null
}

export function AIInsightsPanel({ prediction, counterfactual }: AIInsightsPanelProps) {
  const { insights, loading } = useInsights(prediction, counterfactual)

  if (!prediction) {
    return <div className="card-p text-ink-secondary">Run a prediction to generate insights.</div>
  }

  return (
    <div className="card-p space-y-3">
      <h3 className="font-display text-lg">AI Insights</h3>
      {loading ? <DNALoader /> : null}
      <div className="grid md:grid-cols-3 gap-3">
        {insights.map((item) => (
          <article key={item.kind} className="rounded-xl bg-surface-1 border border-[rgba(0,200,150,0.18)] p-3">
            <div className="label">{item.title}</div>
            <p className="text-sm text-ink-secondary mt-1">{item.text}</p>
          </article>
        ))}
      </div>
    </div>
  )
}
