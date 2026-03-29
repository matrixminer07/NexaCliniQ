import clsx from 'clsx'
import type { Verdict } from '@/types'

interface VerdictBadgeProps {
  verdict: Verdict
}

export function VerdictBadge({ verdict }: VerdictBadgeProps) {
  const label = verdict.verdict === 'PASS' ? 'Ready' : verdict.verdict === 'CAUTION' ? 'Almost there' : 'Needs work'
  return (
    <span
      className={clsx(
        'rounded-xl px-3 py-1.5 text-sm border',
        verdict.verdict === 'PASS' && 'bg-[rgba(0,200,150,0.12)] text-state-pass border-[rgba(0,200,150,0.25)]',
        verdict.verdict === 'CAUTION' && 'bg-[rgba(245,166,35,0.12)] text-state-caution border-[rgba(245,166,35,0.25)]',
        verdict.verdict === 'FAIL' && 'bg-[rgba(255,107,107,0.12)] text-state-fail border-[rgba(255,107,107,0.25)]',
      )}
    >
      {label}
    </span>
  )
}
