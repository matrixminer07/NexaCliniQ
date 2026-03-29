import { Card, Typography } from 'antd'
import { strategyHeaders, strategyMetricRows } from '@/components/strategy/novacuraData'

export function StrategyTab() {
  const toneClass: Record<'green' | 'yellow' | 'red', string> = {
    green: 'bg-green-500/20 text-green-300 border-green-500/40',
    yellow: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    red: 'bg-red-500/20 text-red-300 border-red-500/40',
  }

  return (
    <section className="space-y-4">
      <Card>
        <Typography.Title level={4} style={{ marginBottom: 8 }}>Strategy Comparison Dashboard</Typography.Title>
        <Typography.Paragraph style={{ marginBottom: 0 }}>
          NexaClinIQ should prioritize Strategy A for strongest combined scientific defensibility, time-to-market, and ROI within the 5-year, ₹500M constraint.
        </Typography.Paragraph>
      </Card>

      <Card title="Three-Option Comparative Analysis">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] border-separate border-spacing-0">
            <thead className="sticky top-0 z-10">
              <tr>
                <th className="bg-surface-1 text-left p-3 border-b border-white/10">Criteria</th>
                <th className="bg-surface-1 text-left p-3 border-b border-white/10">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                        <path d="M3 19h18v2H3v-2zm1-13 5 4 3-6 3 6 5-4-2 10H6L4 6z" />
                      </svg>
                    </span>
                    <span>{strategyHeaders.a}</span>
                  </div>
                </th>
                <th className="bg-surface-1 text-left p-3 border-b border-white/10">{strategyHeaders.b}</th>
                <th className="bg-surface-1 text-left p-3 border-b border-white/10">{strategyHeaders.c}</th>
              </tr>
            </thead>
            <tbody>
              {strategyMetricRows.map((row) => (
                <tr key={row.metric}>
                  <td className="p-3 border-b border-white/10 text-ink-secondary">{row.metric}</td>
                  <td className="p-3 border-b border-white/10">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span>{row.strategyA.label}</span>
                      <span className={`text-xs px-2 py-1 rounded-full border ${toneClass[row.strategyA.tone]}`}>{row.strategyA.score.toFixed(1)}/10</span>
                    </div>
                  </td>
                  <td className="p-3 border-b border-white/10">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span>{row.strategyB.label}</span>
                      <span className={`text-xs px-2 py-1 rounded-full border ${toneClass[row.strategyB.tone]}`}>{row.strategyB.score.toFixed(1)}/10</span>
                    </div>
                  </td>
                  <td className="p-3 border-b border-white/10">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span>{row.strategyC.label}</span>
                      <span className={`text-xs px-2 py-1 rounded-full border ${toneClass[row.strategyC.tone]}`}>{row.strategyC.score.toFixed(1)}/10</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Recommendation Context">
        <div className="grid sm:grid-cols-3 gap-3 text-sm">
          <div className="p-3 rounded-xl bg-surface-1 border border-white/10">
            <div className="text-ink-secondary">Speed to market</div>
            <div className="font-semibold">~2 years faster than Strategy B</div>
          </div>
          <div className="p-3 rounded-xl bg-surface-1 border border-white/10">
            <div className="text-ink-secondary">Capital efficiency</div>
            <div className="font-semibold">High upside within ₹500M ceiling</div>
          </div>
          <div className="p-3 rounded-xl bg-surface-1 border border-white/10">
            <div className="text-ink-secondary">Defensibility</div>
            <div className="font-semibold">Strong data flywheel and IP moat</div>
          </div>
        </div>
      </Card>
    </section>
  )
}
