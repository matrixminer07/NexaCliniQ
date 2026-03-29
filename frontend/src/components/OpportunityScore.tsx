import { useMemo } from 'react'
import type { AdmetProfile, TherapeuticArea } from '@/types'

interface OpportunityScoreProps {
  probability: number
  admet: AdmetProfile
  therapeuticArea: TherapeuticArea
}

const TA_WEIGHTS: Record<TherapeuticArea, number> = {
  oncology: 1,
  cns: 0.9,
  rare: 1.1,
  cardiology: 0.95,
  infectious: 0.92,
  metabolic: 0.9,
}

export function OpportunityScore({ probability, admet, therapeuticArea }: OpportunityScoreProps) {
  const score = useMemo(() => {
    const base = probability * 60
    const admetBonus = (admet.lipinski_pass ? 15 : 0) + (!admet.herg_risk ? 10 : 0) + ((admet.bbb_likely ?? false) ? 8 : 0)
    const marketFactor = TA_WEIGHTS[therapeuticArea] * 7
    return Math.min(100, base + admetBonus + marketFactor)
  }, [admet, probability, therapeuticArea])

  const stroke = score < 50 ? 'var(--state-fail)' : score < 70 ? 'var(--state-caution)' : 'var(--state-pass)'
  const label = score < 50 ? 'Needs work' : score < 70 ? 'Promising' : 'Strong candidate'
  const circumference = 2 * Math.PI * 44
  const offset = circumference - (score / 100) * circumference

  return (
    <div className="card-p flex flex-col items-center justify-center">
      <div className="label">Opportunity Score</div>
      <svg viewBox="0 0 120 120" className="w-32 h-32 -rotate-90">
        <circle cx="60" cy="60" r="44" stroke="rgba(0,200,150,0.1)" strokeWidth="8" fill="none" />
        <circle
          cx="60"
          cy="60"
          r="44"
          stroke={stroke}
          strokeWidth="8"
          strokeLinecap="round"
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.6s ease-out' }}
        />
      </svg>
      <div className="metric-value -mt-20">{score.toFixed(0)}</div>
      <div className="text-sm text-ink-secondary mt-8">{label}</div>
    </div>
  )
}
