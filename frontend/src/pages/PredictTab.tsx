import { FormEvent, useMemo, useState } from 'react'
import { AxiosError } from 'axios'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { useAppStore } from '@/store'
import { CardSkeleton } from '@/components/skeletons/CardSkeleton'
import { GlossaryTooltip } from '@/components/GlossaryTooltip'
import { getConfidenceLabel } from '@/utils/confidence'
import { DecisionRationale } from '@/components/DecisionRationale'
import { buildLocalPredictionResponse } from '@/utils/localPrediction'

type PredictError = {
  error?: string
}

function verdictClass(probability: number) {
  if (probability >= 0.7) return 'bg-[#DCFCE7] text-[#166534]'
  if (probability >= 0.4) return 'bg-[#FEF3C7] text-[#92400E]'
  return 'bg-[#FEE2E2] text-[#991B1B]'
}

export function PredictTab() {
  const navigate = useNavigate()
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

  const localPreview = useMemo(
    () => buildLocalPredictionResponse({ ...features, compound_name: compoundName }),
    [compoundName, features],
  )

  const visiblePrediction = prediction ?? localPreview

  const ciLow = visiblePrediction?.confidence_interval?.p10 ?? 0
  const ciHigh = visiblePrediction?.confidence_interval?.p90 ?? 0
  const confidence = visiblePrediction ? getConfidenceLabel(Math.max(0, ciHigh - ciLow)) : null
  const successPct = visiblePrediction ? (visiblePrediction.success_probability * 100).toFixed(1) : '0.0'
  const primaryVerdict = visiblePrediction
    ? visiblePrediction.success_probability >= 0.7
      ? 'Strong Candidate'
      : visiblePrediction.success_probability >= 0.4
        ? 'Needs Optimization'
        : 'High Risk'
    : 'Awaiting signal'

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
      const rawMessage = axiosErr.response?.data?.error || axiosErr.message || 'Prediction request failed'
      const normalized = rawMessage.toLowerCase()
      if (normalized.includes('authorization token required') || normalized.includes('401')) {
        setError('Session expired. Please sign in again and retry prediction.')
        navigate('/login', { replace: true })
      } else if (normalized.includes('network error')) {
        setError('Cannot reach backend API. Ensure server is running on port 5000.')
      } else {
        setError(rawMessage)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="space-y-5">
      <div className="pn-predict-hero card-p overflow-hidden">
        <div className="pn-predict-orb" />
        <div className="relative z-10 grid gap-5 lg:grid-cols-[1.3fr_0.7fr] lg:items-end">
          <div className="space-y-3">
            <p className="pn-predict-kicker">Decision Workspace</p>
            <h2 className="pn-predict-title">Predict</h2>
            <p className="pn-predict-copy">
              Enter molecular properties, run the model, and read the result as an executive signal rather than a raw score.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 sm:gap-3 min-w-0">
            <div className="pn-predict-stat">
              <div className="pn-predict-stat-label">Prediction</div>
              <div className="pn-predict-stat-value">{successPct}%</div>
            </div>
            <div className="pn-predict-stat">
              <div className="pn-predict-stat-label">Verdict</div>
              <div className="pn-predict-stat-value pn-predict-stat-value--tight">{primaryVerdict}</div>
            </div>
            <div className="pn-predict-stat">
              <div className="pn-predict-stat-label">Model</div>
              <div className="pn-predict-stat-value pn-predict-stat-value--tight">Signal Room</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
        <form onSubmit={onSubmit} className="card-p space-y-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="font-display text-xl">Input Panel</h3>
              <p className="text-sm text-ink-secondary">Tune the molecular properties and run a single-compound prediction.</p>
            </div>
            <span className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${verdictClass(visiblePrediction?.success_probability ?? 0)}`}>
              {loading ? 'Running model' : primaryVerdict}
            </span>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            {(
              Object.keys(formValues) as Array<keyof typeof formValues>
            ).map((key) => (
              <label key={key} className="space-y-1">
                <div className="text-xs uppercase tracking-[0.08em] text-ink-secondary">{key.replace('_', ' ')}</div>
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

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <button type="submit" className="btn-primary inline-flex items-center justify-center gap-2 px-6 py-3 text-base disabled:opacity-70" disabled={loading}>
              {loading ? 'Predicting...' : 'Run Prediction'}
            </button>
            <div className="text-sm text-ink-secondary">
              The dashboard will surface confidence, phase probabilities, and the rationale automatically.
            </div>
          </div>

          {error ? <div className="rounded-xl border border-state-fail/30 bg-state-fail/10 px-4 py-3 text-sm text-state-fail">{error}</div> : null}
        </form>

        <div className="space-y-5">
          <div className="card-p pn-predict-result space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-sm uppercase tracking-[0.12em] text-ink-secondary">Prediction Result</div>
                <div className="text-3xl font-semibold leading-none">{successPct}%</div>
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
              <GlossaryTooltip term="ci_width">Confidence interval</GlossaryTooltip>: {visiblePrediction?.confidence_interval.p10?.toFixed(2) ?? '0.00'} to {visiblePrediction?.confidence_interval.p90?.toFixed(2) ?? '0.00'}
            </div>

            <div className="h-2 rounded-full bg-surface-2">
              <div
                className="h-2 rounded-full bg-gradient-to-r from-cyan-400 via-brand to-emerald-400 transition-all duration-500"
                style={{ width: `${visiblePrediction?.success_probability ? visiblePrediction.success_probability * 100 : 12}%` }}
              />
            </div>

            <span className={`inline-flex w-fit rounded-full px-3 py-1 text-xs font-medium ${verdictClass(visiblePrediction?.success_probability ?? 0)}`}>
              {primaryVerdict}
            </span>

            {visiblePrediction?.phase_probabilities ? (
              <div className="space-y-2 pt-1">
                <div className="text-xs uppercase tracking-[0.08em] text-ink-secondary">
                  <GlossaryTooltip term="phase_pos">Phase probabilities</GlossaryTooltip>
                </div>
                <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                  {Object.entries(visiblePrediction.phase_probabilities).slice(0, 4).map(([key, value]) => (
                    <div key={key} className="rounded-xl border border-white/8 bg-white/5 px-3 py-3">
                      <div className="text-xs text-ink-secondary capitalize">{key.replace(/_/g, ' ')}</div>
                      <div className="font-mono text-base font-semibold">{Number(value).toFixed(1)}%</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>

          {visiblePrediction?.shap_breakdown ? (
            <div className="rounded-[1.25rem] border border-[rgba(99,102,241,0.30)] bg-[linear-gradient(180deg,rgba(99,102,241,0.10),rgba(15,23,42,0.72))] p-1 shadow-[0_0_0_1px_rgba(255,255,255,0.02),0_24px_80px_rgba(0,0,0,0.28)]">
              <DecisionRationale shapBreakdown={visiblePrediction.shap_breakdown} score={visiblePrediction.success_probability} />
            </div>
          ) : (
            <div className="card-p space-y-3 border-dashed border-[rgba(148,163,184,0.24)]">
              <div className="text-sm uppercase tracking-[0.12em] text-ink-secondary">Decision Rationale</div>
              <div className="text-sm text-ink-secondary">
                Run a prediction to unlock the contribution view, phase probabilities, and the full explanation stack.
              </div>
              <div className="grid gap-2 sm:grid-cols-3">
                <div className="rounded-xl bg-white/5 px-3 py-3">
                  <div className="text-xs text-ink-secondary">Clarity</div>
                  <div className="font-semibold">Executive-ready</div>
                </div>
                <div className="rounded-xl bg-white/5 px-3 py-3">
                  <div className="text-xs text-ink-secondary">Mode</div>
                  <div className="font-semibold">Interactive</div>
                </div>
                <div className="rounded-xl bg-white/5 px-3 py-3">
                  <div className="text-xs text-ink-secondary">Output</div>
                  <div className="font-semibold">Probability + rationale</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

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
