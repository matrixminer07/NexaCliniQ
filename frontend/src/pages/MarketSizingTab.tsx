import { useEffect, useMemo, useRef, useState } from 'react'
import { Card } from 'antd'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { api } from '@/services/api'
import { DarkTooltip } from '@/components/DarkTooltip'
import { downloadCsv, exportChartAsPng } from '@/utils/export'

const FALLBACK = {
  global_pharma: {
    TAM_label: '$1.48T',
    SAM_label: '$310B',
    SOM_label: '$4.0B',
    cagr: 29.6,
  },
  therapeutic_breakdown: [
    { area: 'Oncology', share_pct: 38, size_bn: 237, growth_pct: 11.2, color: '#00C896' },
    { area: 'Immunology', share_pct: 18, size_bn: 112, growth_pct: 9.8, color: '#4DA6FF' },
    { area: 'CNS', share_pct: 14, size_bn: 87, growth_pct: 7.4, color: '#7F77DD' },
    { area: 'Cardiovascular', share_pct: 11, size_bn: 68, growth_pct: 6.1, color: '#F5A623' },
    { area: 'Rare Disease', share_pct: 9, size_bn: 56, growth_pct: 14.3, color: '#FF6B6B' },
    { area: 'Infectious', share_pct: 6, size_bn: 37, growth_pct: 8.9, color: '#9FE1CB' },
    { area: 'Metabolic', share_pct: 4, size_bn: 25, growth_pct: 12.7, color: '#FAC775' },
  ],
}

type MarketDataShape = typeof FALLBACK

export function MarketSizingTab() {
  const [data, setData] = useState<MarketDataShape>(FALLBACK)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const chartRef = useRef<HTMLDivElement | null>(null)

  const load = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.marketData()
      const merged = {
        ...FALLBACK,
        ...(response as Partial<MarketDataShape>),
        therapeutic_breakdown:
          ((response as { therapeutic_breakdown?: MarketDataShape['therapeutic_breakdown'] })?.therapeutic_breakdown ||
            FALLBACK.therapeutic_breakdown).map((item, index) => ({
            ...item,
            color: item.color || FALLBACK.therapeutic_breakdown[index % FALLBACK.therapeutic_breakdown.length].color,
          })),
      }
      setData(merged)
    } catch {
      setError('Using fallback market sizing data.')
      setData(FALLBACK)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const exportRows = useMemo(
    () =>
      data.therapeutic_breakdown.map((item) => ({
        area: item.area,
        share_pct: item.share_pct,
        size_bn: item.size_bn,
        growth_pct: item.growth_pct,
      })),
    [data.therapeutic_breakdown],
  )

  const m = data.global_pharma

  return (
    <section className="space-y-4">
      <div className="flex justify-end gap-2">
        <button
          type="button"
          className="btn-ghost"
          aria-label="Export market data CSV"
          onClick={() => downloadCsv('market-sizing-data.csv', exportRows)}
          disabled={loading}
        >
          Export CSV
        </button>
        <button
          type="button"
          className="btn-ghost"
          aria-label="Export market chart as PNG"
          onClick={() => void exportChartAsPng(chartRef.current, 'market-sizing-chart')}
          disabled={loading}
        >
          Export PNG
        </button>
        <button type="button" className="btn-ghost" aria-label="Refresh market sizing" onClick={() => void load()}>
          ↻
        </button>
      </div>
      <Card>
        <h2 className="font-display text-lg" style={{ marginBottom: 8 }}>
          Market Opportunity Model
        </h2>
        <p style={{ marginBottom: 0 }}>
          Strategy-grade TAM/SAM/SOM sizing from public pharma market datasets.
        </p>
      </Card>

      {error ? <div className="text-sm text-ink-secondary">{error}</div> : null}

      <div className="grid md:grid-cols-3 gap-3">
        <div className="card-p">
          <div className="text-xs uppercase tracking-[0.12em] text-ink-secondary">TAM</div>
          <div className="text-3xl font-semibold mt-1" style={{ color: '#4DA6FF', opacity: loading ? 0.8 : 1 }}>{m.TAM_label}</div>
        </div>
        <div className="card-p">
          <div className="text-xs uppercase tracking-[0.12em] text-ink-secondary">SAM</div>
          <div className="text-3xl font-semibold mt-1" style={{ color: '#00C896', opacity: loading ? 0.8 : 1 }}>{m.SAM_label}</div>
        </div>
        <div className="card-p">
          <div className="text-xs uppercase tracking-[0.12em] text-ink-secondary">SOM</div>
          <div className="text-3xl font-semibold mt-1" style={{ color: '#F5A623', opacity: loading ? 0.8 : 1 }}>{m.SOM_label}</div>
        </div>
      </div>

      <div className="card-p" ref={chartRef}>
        <h3 className="font-display text-base mb-3">Therapeutic area market mix</h3>
        <div className="grid md:grid-cols-2 gap-4 items-center">
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data.therapeutic_breakdown}
                  cx="50%"
                  cy="50%"
                  innerRadius={70}
                  outerRadius={120}
                  dataKey="share_pct"
                  paddingAngle={2}
                >
                  {data.therapeutic_breakdown.map((item) => (
                    <Cell key={item.area} fill={item.color} />
                  ))}
                </Pie>
                <Tooltip content={<DarkTooltip formatter={(value) => `${value}%`} />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div>
            {data.therapeutic_breakdown.map((item) => (
              <div key={item.area} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid rgba(0,200,150,0.06)' }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: item.color, flexShrink: 0 }} />
                <div style={{ flex: 1, fontSize: 13 }}>{item.area}</div>
                <div style={{ fontFamily: 'IBM Plex Mono', fontSize: 13, color: '#00C896' }}>${item.size_bn}B</div>
                <div style={{ fontFamily: 'IBM Plex Mono', fontSize: 12, color: '#F5A623' }}>+{item.growth_pct}%</div>
                <div style={{ fontFamily: 'IBM Plex Mono', fontSize: 12, color: '#8BA89F', width: 36, textAlign: 'right' }}>{item.share_pct}%</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
