import { FormEvent, useState } from 'react'
import { AxiosError } from 'axios'
import { api } from '@/services/api'
import { useAppStore } from '@/store'
import { CardSkeleton } from '@/components/skeletons/CardSkeleton'
import { GlossaryTooltip } from '@/components/GlossaryTooltip'
import { getConfidenceLabel } from '@/utils/confidence'
import { DecisionRationale } from '@/components/DecisionRationale'

type PredictError = {
  error?: string
}

function verdictClass(probability: number) {
  if (probability >= 0.7) return 'bg-[#DCFCE7] text-[#166534]'
  if (probability >= 0.4) return 'bg-[#FEF3C7] text-[#92400E]'
  return 'bg-[#FEE2E2] text-[#991B1B]'
}

export function PredictTab() {
  const features = useAppStore((s) => s.featuresA)
  const setFeatureA = useAppStore((s) => s.setFeatureA)
  const prediction = useAppStore((s) => s.prediction)
  const setPrediction = useAppStore((s) => s.setPrediction)
  const setCounterfactual = useAppStore((s) => s.setCounterfactual)
  const compoundName = useAppStore((s) => s.compoundName)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [formValues, setFormValues] = useState({
    toxicity: String(features.toxicity),
    bioavailability: String(features.bioavailability),
    solubility: String(features.solubility),
    binding: String(features.binding),
    molecular_weight: String(features.molecular_weight),
  })

  const ciLow = prediction?.confidence_interval?.p10 ?? 0
  const ciHigh = prediction?.confidence_interval?.p90 ?? 0
  const confidence = prediction ? getConfidenceLabel(Math.max(0, ciHigh - ciLow)) : null

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setError('')

    try {
      const payload = {
        compound_name: compoundName,
        toxicity: parseFloat(formValues.toxicity),
        bioavailability: parseFloat(formValues.bioavailability),
        solubility: parseFloat(formValues.solubility),
        binding: parseFloat(formValues.binding),
        molecular_weight: parseFloat(formValues.molecular_weight),
      }

      const predictionResult = await api.predict(payload)
      setPrediction(predictionResult)

      try {
        const cf = await api.counterfactual({
          toxicity: payload.toxicity,
          bioavailability: payload.bioavailability,
          solubility: payload.solubility,
          binding: payload.binding,
          molecular_weight: payload.molecular_weight,
          target_probability: 0.75,
        })
        setCounterfactual(cf)
      } catch {
        setCounterfactual(null)
      }
    } catch (err) {
      const axiosErr = err as AxiosError<PredictError>
      setError(axiosErr.response?.data?.error || axiosErr.message || 'Prediction request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="space-y-4">
      <form onSubmit={onSubmit} className="card-p space-y-4">
        <div>
          <h2 className="font-display text-lg">Predict</h2>
          <p className="text-sm text-ink-secondary">Enter molecular properties and run a single-compound prediction.</p>
        </div>

        <div className="grid md:grid-cols-2 gap-3">
          {(
            Object.keys(formValues) as Array<keyof typeof formValues>
          ).map((key) => (
            <label key={key} className="space-y-1">
              <div className="text-xs text-ink-secondary">{key.replace('_', ' ')}</div>
              <input
                className="input"
                placeholder="0.00"
                value={formValues[key]}
                onChange={(e) => {
                  const value = e.target.value
                  setFormValues((prev) => ({ ...prev, [key]: value }))
                  const parsed = parseFloat(value)
                  if (!Number.isNaN(parsed)) {
                    setFeatureA(key, parsed)
                  }
                }}
              />
            </label>
          ))}
        </div>

        <button type="submit" className="btn-primary inline-flex items-center gap-2 disabled:opacity-70" disabled={loading}>
          {loading ? 'Predicting...' : 'Run Prediction'}
        </button>

        {error ? <div className="text-sm text-state-fail">{error}</div> : null}
      </form>

      {prediction ? (
        <div className="card-p space-y-3">
          <div className="text-sm text-ink-secondary">Prediction Result</div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="text-[40px] leading-none font-semibold">
              {(prediction.success_probability * 100).toFixed(1)}%
            </div>
            {confidence ? (
              <span
                className="inline-flex rounded-full px-3 py-1 text-xs font-medium"
                style={{ background: `${confidence.colorHex}1A`, color: confidence.colorHex }}
                title={confidence.description}
              >
                {confidence.label}
              </span>
            ) : null}
          </div>
          <div className="text-sm text-ink-secondary">
            <GlossaryTooltip term="ci_width">Confidence interval</GlossaryTooltip>: {prediction.confidence_interval.p10?.toFixed(2)} to {prediction.confidence_interval.p90?.toFixed(2)}
          </div>
          <span className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${verdictClass(prediction.success_probability)}`}>
            {prediction.success_probability >= 0.7 ? 'Strong Candidate' : prediction.success_probability >= 0.4 ? 'Needs Optimization' : 'High Risk'}
          </span>

          {prediction.phase_probabilities ? (
            <div className="space-y-2 pt-1">
              <div className="text-xs uppercase tracking-[0.08em] text-ink-secondary">
                <GlossaryTooltip term="phase_pos">Phase probabilities</GlossaryTooltip>
              </div>
              <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                {Object.entries(prediction.phase_probabilities).slice(0, 4).map(([key, value]) => (
                  <div key={key} className="rounded-md bg-surface-1 px-3 py-2">
                    <div className="text-xs text-ink-secondary capitalize">{key.replace(/_/g, ' ')}</div>
                    <div className="font-mono text-sm">{Number(value).toFixed(1)}%</div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      {prediction?.shap_breakdown ? (
        <DecisionRationale shapBreakdown={prediction.shap_breakdown} score={prediction.success_probability} />
      ) : null}

      {loading ? (
        <div className="grid gap-3 md:grid-cols-3">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : null}
    </section>
  )
}
