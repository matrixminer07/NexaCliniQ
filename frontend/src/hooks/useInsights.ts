import { useEffect, useMemo, useRef, useState } from 'react'
import type { CounterfactualResponse, InsightCard, PredictionResponse } from '@/types'

export function useInsights(prediction: PredictionResponse | null, counterfactual: CounterfactualResponse | null) {
  const [insights, setInsights] = useState<InsightCard[]>([])
  const [loading, setLoading] = useState(false)
  const timer = useRef<number | undefined>(undefined)

  const localFallback = useMemo((): InsightCard[] => {
    if (!prediction) return []
    const top = prediction.shap_breakdown.contributions[0]
    const firstChange = counterfactual?.changes_required?.[0]
    const strength = top ? `${top.feature} is your strongest positive driver right now.` : 'The profile has balanced strengths across drivers.'
    const opportunity = firstChange
      ? `Most efficient uplift: ${firstChange.direction} ${firstChange.feature} to ${firstChange.suggested.toFixed(2)}.`
      : 'Counterfactual target is already met. Focus on robust execution.'
    const verdict = prediction.verdict.verdict === 'PASS' ? 'Ready for pre-clinical planning and parallel ADMET confirmation.' : 'Prioritize one property shift before the next funding gate.'
    return [
      { kind: 'strength', title: 'Strength', text: strength },
      { kind: 'opportunity', title: 'Opportunity', text: opportunity },
      { kind: 'next', title: 'Next Step', text: verdict },
    ]
  }, [prediction, counterfactual])

  useEffect(() => {
    if (!prediction) {
      setInsights([])
      return
    }
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => {
      setLoading(true)
      setInsights(localFallback)
      setLoading(false)
    }, 800)

    return () => window.clearTimeout(timer.current)
  }, [prediction, localFallback])

  return { insights, loading }
}
