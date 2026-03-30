import { useEffect, useState } from 'react'
import { Card } from 'antd'
import { api } from '@/services/api'
import { CardSkeleton } from '@/components/skeletons/CardSkeleton'
import { TextSkeleton } from '@/components/skeletons/TextSkeleton'

interface ExecutiveSummaryData {
  recommendation?: {
    recommendation_statement?: string
    primary_choice?: string
    confidence_level_pct?: number
  }
  market_context?: {
    market_insight?: string
  }
  board_approval_points?: string[]
}

export function ExecutiveSummaryTab() {
  const [data, setData] = useState<ExecutiveSummaryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const load = async () => {
    try {
      setLoading(true)
      setError(false)
      const response = await api.executiveSummary()
      setData(response as ExecutiveSummaryData)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const run = async () => {
      await load()
    }

    run()
  }, [])

  if (loading) {
    return (
      <section className="space-y-3 card-p">
        <TextSkeleton lines={4} />
        <div className="grid md:grid-cols-2 gap-3">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </section>
    )
  }

  if (error) {
    return (
      <section>
        <div className="rounded-[8px] border border-[rgba(148,163,184,0.25)] bg-surface-1 p-4 text-ink-secondary">
          Executive summary is currently unavailable. Please try again shortly.
        </div>
      </section>
    )
  }

  const statement = data?.recommendation?.recommendation_statement || 'N/A'
  const primaryChoice = data?.recommendation?.primary_choice || 'N/A'
  const confidence =
    typeof data?.recommendation?.confidence_level_pct === 'number'
      ? `${data.recommendation.confidence_level_pct.toFixed(1)}%`
      : 'N/A'
  const insight = data?.market_context?.market_insight || 'N/A'
  const approvalPoints = data?.board_approval_points || []

  return (
    <section className="space-y-4">
      <div className="flex justify-end">
        <button type="button" className="btn-ghost" aria-label="Refresh executive summary" onClick={() => void load()}>
          ↻
        </button>
      </div>
      <Card title="Executive Recommendation">
        <div className="space-y-2">
          <div>
            <div className="text-xs uppercase tracking-[0.12em] text-ink-secondary">Primary Choice</div>
            <div className="font-semibold">{primaryChoice}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-[0.12em] text-ink-secondary">Confidence</div>
            <div className="font-semibold">{confidence}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-[0.12em] text-ink-secondary">Statement</div>
            <div>{statement}</div>
          </div>
        </div>
      </Card>

      <Card title="Market Insight">
        <div>{insight}</div>
      </Card>

      <Card title="Board Approval Points">
        {approvalPoints.length === 0 ? (
          <div className="text-ink-secondary">N/A</div>
        ) : (
          <ul className="list-disc pl-5 space-y-1">
            {approvalPoints.map((point, index) => (
              <li key={`${point}-${index}`}>{point}</li>
            ))}
          </ul>
        )}
      </Card>
    </section>
  )
}
