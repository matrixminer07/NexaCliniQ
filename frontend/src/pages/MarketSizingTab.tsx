import { Card, Col, Row, Typography } from 'antd'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useMarketData } from '@/hooks/useMarketData'
import { CardSkeleton } from '@/components/skeletons/CardSkeleton'
import { ChartSkeleton } from '@/components/skeletons/ChartSkeleton'

const colors = ['#2563EB', '#0EA5E9', '#14B8A6']

function formatInr(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(value)
}

export function MarketSizingTab() {
  const { data, chartData, loading, error, refetch } = useMarketData()

  const tam = data?.market?.tam_busd
  const sam = data?.market?.sam_busd
  const som = data?.market?.som_busd

  return (
    <section className="space-y-4">
      <div className="flex justify-end">
        <button type="button" className="btn-ghost" aria-label="Refresh market sizing" onClick={() => void refetch?.()}>
          ↻
        </button>
      </div>
      <Card>
        <Typography.Title level={4} style={{ marginBottom: 8 }}>
          Market Opportunity Model
        </Typography.Title>
        <Typography.Paragraph style={{ marginBottom: 0 }}>
          Strategy-grade TAM/SAM/SOM sizing mapped directly from the market service feed.
        </Typography.Paragraph>
      </Card>

      {loading ? (
        <>
          <div className="grid md:grid-cols-3 gap-3">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
          <ChartSkeleton />
          <ChartSkeleton />
        </>
      ) : null}

      {!loading ? (
        <>
          <Row gutter={[12, 12]}>
            <Col xs={24} md={8}>
              <Card>
                <div className="text-xs uppercase tracking-[0.12em] text-ink-secondary">TAM</div>
                <div className="text-2xl font-semibold mt-1">{formatInr(typeof tam === 'number' ? tam : null)}</div>
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card>
                <div className="text-xs uppercase tracking-[0.12em] text-ink-secondary">SAM</div>
                <div className="text-2xl font-semibold mt-1">{formatInr(typeof sam === 'number' ? sam : null)}</div>
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card>
                <div className="text-xs uppercase tracking-[0.12em] text-ink-secondary">SOM</div>
                <div className="text-2xl font-semibold mt-1">{formatInr(typeof som === 'number' ? som : null)}</div>
              </Card>
            </Col>
          </Row>

          <Card title="Market Mix Chart">
            <div style={{ height: 300, width: '100%' }}>
              {error ? (
                <div className="h-full flex items-center justify-center text-ink-secondary">Market data is currently unavailable.</div>
              ) : !chartData || chartData.length === 0 ? (
                <div className="h-full flex items-center justify-center text-ink-secondary">No data available</div>
              ) : (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie data={chartData} dataKey="value" nameKey="name" outerRadius={110}>
                      {chartData.map((entry, index) => (
                        <Cell key={entry.name} fill={colors[index % colors.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: number) => formatInr(value)} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>
        </>
      ) : null}
    </section>
  )
}
