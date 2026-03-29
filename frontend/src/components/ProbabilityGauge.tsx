import CountUp from 'react-countup'

interface ProbabilityGaugeProps {
  probability: number
  p10?: number
  p90?: number
  baseline?: number
}

export function ProbabilityGauge({ probability, p10 = 0.45, p90 = 0.85, baseline = 0.32 }: ProbabilityGaugeProps) {
  const percent = Math.max(0, Math.min(100, probability * 100))
  const angle = -90 + (percent / 100) * 180
  const delta = (probability - baseline) * 100

  return (
    <div className="card-p relative overflow-hidden">
      <div className="label mb-3">Opportunity Probability</div>
      <div className="relative h-40 flex items-end justify-center">
        <div className="absolute bottom-0 w-56 h-28 rounded-t-full border-8 border-b-0 border-[rgba(0,200,150,0.2)]" />
        <div className="absolute bottom-0 w-56 h-28 rounded-t-full border-8 border-b-0 border-transparent border-t-[var(--state-pass)]" style={{ clipPath: 'inset(0 0 0 50%)' }} />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 origin-bottom h-20 w-1 bg-ink-primary rounded-full" style={{ transform: `translateX(-50%) rotate(${angle}deg)`, transition: 'transform 600ms cubic-bezier(0.34, 1.56, 0.64, 1)' }} />
        <div className="absolute bottom-1 left-1/2 -translate-x-1/2 w-4 h-4 rounded-full bg-brand" />
        <div className="absolute text-center bottom-4">
          <div className="metric-value">
            <CountUp end={percent} decimals={1} duration={0.6} />%
          </div>
          <div className="text-xs text-ink-secondary font-mono">vs baseline {delta >= 0 ? '+' : ''}{delta.toFixed(1)}pp</div>
          <div className="text-xs text-ink-tertiary font-mono mt-1">P10 {Math.round(p10 * 100)}% • P90 {Math.round(p90 * 100)}%</div>
        </div>
      </div>
    </div>
  )
}
