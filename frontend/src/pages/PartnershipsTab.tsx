import { useMemo, useState } from 'react'
import { Card, Typography } from 'antd'
import { partners, type PartnerType } from '@/components/strategy/novacuraData'

export function PartnershipsTab() {
  const [filter, setFilter] = useState<'All' | PartnerType>('All')

  const filtered = useMemo(() => {
    if (filter === 'All') return partners
    return partners.filter((item) => item.type === filter)
  }, [filter])

  const fitClass: Record<'A' | 'B' | 'C', string> = {
    A: 'bg-green-500/20 text-green-300 border-green-500/40',
    B: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    C: 'bg-blue-500/20 text-blue-300 border-blue-500/40',
  }

  return (
    <section className="space-y-4">
      <Card>
        <Typography.Title level={4} style={{ marginBottom: 8 }}>Partnerships Map</Typography.Title>
        <Typography.Paragraph style={{ marginBottom: 0 }}>
          Targeted partners strengthen AI infrastructure, translational execution, and commercialization options.
        </Typography.Paragraph>
      </Card>

      <Card>
        <div className="flex flex-wrap gap-2 mb-4">
          {(['All', 'AI/Tech', 'CRO', 'Pharma', 'Data'] as const).map((key) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-3 py-1 rounded-full text-sm border ${filter === key ? 'bg-brand-subtle text-brand border-brand/40' : 'border-white/20 text-ink-secondary'}`}
            >
              {key}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {filtered.map((partner) => (
            <div key={partner.name} className="rounded-xl border border-white/10 bg-surface-1 p-4 shadow-lg">
              <div className="flex items-center gap-3 mb-3">
                <div className="h-10 w-10 rounded-lg bg-white/10 flex items-center justify-center text-xs text-ink-secondary">
                  Logo
                </div>
                <div>
                  <div className="font-semibold">{partner.name}</div>
                  <div className="text-xs text-ink-secondary">{partner.type}</div>
                </div>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-ink-secondary">Relevance score</span>
                <span className="font-semibold">{partner.relevanceScore.toFixed(1)}/10</span>
              </div>
              <div className="mt-3">
                <span className={`inline-flex px-2 py-1 text-xs rounded-full border ${fitClass[partner.strategyFit]}`}>
                  Strategy fit: {partner.strategyFit}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </section>
  )
}
