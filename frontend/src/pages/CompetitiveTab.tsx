import { Card, Typography } from 'antd'
import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'
import { marketAreaColors, marketBubbles } from '@/components/strategy/novacuraData'

export function CompetitiveTab() {
  const areas = ['Oncology', 'Rare Disease', 'CNS', 'Platform'] as const
  const byArea = areas.map((area) => ({
    area,
    data: marketBubbles.filter((item) => item.area === area),
  }))

  const maxMarketCap = Math.max(...marketBubbles.map((item) => item.marketCap))

  if (!marketBubbles || marketBubbles.length === 0) {
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
        <ResponsiveContainer width="100%" height={300}>
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
            <XAxis
              type="number"
              dataKey="maturity"
              name="Market Maturity"
              domain={[0, 10]}
              label={{ value: 'Market Maturity (0-10)', position: 'insideBottom', offset: -2 }}
            />
            <YAxis
              type="number"
              dataKey="aiIntegration"
              name="AI Integration"
              domain={[0, 10]}
              label={{ value: 'AI Integration Level (0-10)', angle: -90, position: 'insideLeft' }}
            />
            <ZAxis type="number" dataKey="marketCap" range={[80, 700]} name="Market cap" />
            <Tooltip
              cursor={{ strokeDasharray: '4 4' }}
              formatter={(value: number, name: string) => {
                if (name === 'Market cap') return [`₹${value}M`, name]
                return [value, name]
              }}
              contentStyle={{ borderRadius: 12, border: '1px solid rgba(255,255,255,0.15)' }}
              labelFormatter={(label) => {
                const hit = marketBubbles.find((item) => item.name === String(label))
                if (!hit) return String(label)
                return `${hit.name} | ₹${hit.marketCap}M | ${hit.keyDrug} | ${hit.aiApproach}`
              }}
            />
            <Legend />
            {byArea.map((entry) => (
              <Scatter
                key={entry.area}
                name={entry.area}
                data={entry.data.map((item) => ({ ...item, z: item.marketCap, fill: marketAreaColors[item.area] }))}
                fill={marketAreaColors[entry.area]}
                shape={(props: any) => {
                  const isNexaClinIQ = props?.payload?.name === 'NexaClinIQ'
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
