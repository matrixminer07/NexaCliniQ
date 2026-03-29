import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '@/services/api'
import { useAppStore } from '@/store'

export function usePrediction() {
  const features = useAppStore((s) => s.featuresA)
  const compoundName = useAppStore((s) => s.compoundName)
  const setPrediction = useAppStore((s) => s.setPrediction)
  const setCounterfactual = useAppStore((s) => s.setCounterfactual)
  const targetProbability = useAppStore((s) => s.targetProbability)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<number | undefined>(undefined)

  const payload = useMemo(() => ({ ...features, compound_name: compoundName }), [features, compoundName])

  useEffect(() => {
    window.clearTimeout(timerRef.current)
    timerRef.current = window.setTimeout(async () => {
      try {
        setLoading(true)
        setError(null)
        const prediction = await api.predict(payload)
        setPrediction(prediction)
        const cf = await api.counterfactual({ ...features, target_probability: targetProbability })
        setCounterfactual(cf)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Prediction failed'
        setError(message)
      } finally {
        setLoading(false)
      }
    }, 300)

    return () => window.clearTimeout(timerRef.current)
  }, [payload, features, targetProbability, setCounterfactual, setPrediction])

  return { loading, error }
}
