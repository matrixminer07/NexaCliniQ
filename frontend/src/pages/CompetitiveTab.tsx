import { useEffect, useMemo, useState } from 'react'
import { Card, Typography } from 'antd'
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'
import { api } from '@/services/api'
import { marketAreaColors, marketBubbles } from '@/components/strategy/novacuraData'
import { DarkTooltip } from '@/components/DarkTooltip'

type PlayerPoint = {
  name: string
  maturity: number
  aiIntegration: number
  marketCap: number
  area: 'Oncology' | 'Rare Disease' | 'CNS' | 'Platform'
}

export function CompetitiveTab() {
  const [points, setPoints] = useState<PlayerPoint[]>(
    marketBubbles.map((item) => ({
      name: item.name,
      maturity: item.maturity,
      aiIntegration: item.aiIntegration,
      marketCap: item.marketCap,
      area: item.area,
    })),
  )

  useEffect(() => {
    const run = async () => {
      try {
        const response = await api.marketData()
        const topPlayers = (response as { top_players?: Array<Record<string, unknown>> }).top_players || []
        if (!topPlayers.length) return

        const normalized = topPlayers.map((player) => {
          const ta = String(player.ta || 'Platform')
          const area: PlayerPoint['area'] =
            ta.includes('Oncology')
              ? 'Oncology'
              : ta.includes('CNS')
                ? 'CNS'
                : ta.includes('Rare')
                  ? 'Rare Disease'
                  : 'Platform'
          return {
            name: String(player.name || 'Unknown'),
            maturity: Number(player.maturity || 0),
            aiIntegration: Number(player.ai_level || 0),
            marketCap: Number(player.valuation_bn || 0) * 1000,
            area,
          }
        })

        setPoints(normalized)
      } catch {
        // Keep local fallback points.
      }
    }
    void run()
  }, [])

  const areas = ['Oncology', 'Rare Disease', 'CNS', 'Platform'] as const
  const byArea = useMemo(
    () =>
      areas.map((area) => ({
        area,
        data: points.filter((item) => item.area === area),
      })),
    [points],
  )

  const maxMarketCap = Math.max(...points.map((item) => item.marketCap), 1)

  if (!points || points.length === 0) {
    return <div className="card-p text-center text-ink-secondary">No data available</div>
  }

  return (
    <section className="space-y-4">
      <Card>
        <Typography.Title level={4} style={{ marginBottom: 8 }}>Market Landscape Chart</Typography.Title>
        <Typography.Paragraph style={{ marginBottom: 0 }}>
          Compare AI-native biotech players by market maturity and AI integration level, with bubble size representing market scale.
        </Typography.Paragraph>
      </Card>

      <Card title="AI Biopharma Positioning">
        <ResponsiveContainer width="100%" aspect={2}>
          <ScatterChart margin={{ top: 20, right: 40, bottom: 40, left: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
            <XAxis
              type="number"
              dataKey="maturity"
              name="Market Maturity"
              domain={[0, 10]}
              tickCount={6}
              tick={{ fill: '#8BA89F', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              label={{ value: 'Market Maturity (0-10)', position: 'insideBottom', offset: -8, fill: '#506860', fontSize: 12 }}
            />
            <YAxis
              type="number"
              dataKey="aiIntegration"
              name="AI Integration"
              domain={[0, 10]}
              tickCount={6}
              tick={{ fill: '#8BA89F', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              label={{ value: 'AI Integration Level', angle: -90, position: 'insideLeft', fill: '#506860', fontSize: 12 }}
            />
            <ZAxis type="number" dataKey="marketCap" range={[80, 700]} name="Market cap" />
            <Tooltip
              cursor={{ strokeDasharray: '4 4' }}
              content={<DarkTooltip formatter={(value) => `${Number(value).toFixed(1)}`} />}
            />
            {byArea.map((entry) => (
              <Scatter
                key={entry.area}
                name={entry.area}
                data={entry.data.map((item) => ({ ...item, z: item.marketCap, fill: marketAreaColors[item.area] }))}
                fill={marketAreaColors[entry.area]}
                shape={(props: any) => {
                  const isNexaClinIQ = props?.payload?.name === 'NexaClinIQ' || props?.payload?.name === 'NovaCura'
                  const radius = Math.max(8, (props?.payload?.marketCap / maxMarketCap) * 26)
                  return (
                    <g>
                      <circle cx={props.cx} cy={props.cy} r={radius} fill={props.fill} opacity={isNexaClinIQ ? 0.95 : 0.7} stroke={isNexaClinIQ ? '#ffffff' : 'rgba(255,255,255,0.35)'} strokeWidth={isNexaClinIQ ? 3 : 1.2} />
                      {isNexaClinIQ ? <text x={props.cx} y={props.cy + 3} textAnchor="middle" fontSize="9" fill="#0b1220">NC</text> : null}
                    </g>
                  )
                }}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </Card>

      <Card title="Legend and Reading Guide">
        <div className="grid sm:grid-cols-2 gap-3 text-sm">
          <div className="p-3 rounded-xl bg-surface-1 border border-white/10">
            <div className="text-ink-secondary mb-1">Bubbles</div>
            <div>Size reflects company market cap/revenue proxy.</div>
          </div>
          <div className="p-3 rounded-xl bg-surface-1 border border-white/10">
            <div className="text-ink-secondary mb-1">Highlight</div>
            <div>NexaClinIQ is outlined in white for quick strategic comparison.</div>
          </div>
        </div>
      </Card>
    </section>
  )
}
