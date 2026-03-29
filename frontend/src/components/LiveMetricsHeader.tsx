import CountUp from 'react-countup'
import { useSocketLiveStats } from '@/services/socket'
import { useAppStore } from '@/store'

export function LiveMetricsHeader() {
  const { totalAnalysed, passRate, yearsSaved } = useAppStore((s) => ({
    totalAnalysed: s.totalAnalysed,
    passRate: s.passRate,
    yearsSaved: s.yearsSaved,
  }))
  useSocketLiveStats()

  return (
    <header className="card-p flex flex-wrap gap-6 items-center justify-between">
      <div className="text-sm text-ink-secondary">Live Program Metrics</div>
      <div className="flex flex-wrap gap-6 text-sm">
        <span className="font-mono"><CountUp end={totalAnalysed} duration={0.8} /> compounds analysed</span>
        <span className="font-mono"><CountUp end={passRate} duration={0.8} decimals={1} />% pass rate</span>
        <span className="font-mono"><CountUp end={yearsSaved} duration={0.8} decimals={1} /> yrs saved vs traditional</span>
      </div>
    </header>
  )
}
