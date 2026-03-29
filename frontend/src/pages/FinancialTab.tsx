import { useMemo, useState } from 'react'
import { Card } from 'antd'
import {
  Line,
  LineChart,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts'
import { defaultRoiInputs, roiCalculator } from '@/components/strategy/novacuraData'

export function FinancialTab() {
  const [allocations, setAllocations] = useState({
    strategyA: defaultRoiInputs.strategyA,
    strategyB: defaultRoiInputs.strategyB,
    strategyC: defaultRoiInputs.strategyC,
  })

  const totalBudget = 500

  const setAllocation = (key: 'strategyA' | 'strategyB' | 'strategyC', nextValue: number) => {
    setAllocations((prev) => {
      const clamped = Math.round(Math.max(0, Math.min(totalBudget, nextValue)))
      const others = (['strategyA', 'strategyB', 'strategyC'] as const).filter((k) => k !== key)
      const currentOtherTotal = prev[others[0]] + prev[others[1]]
      const remainder = totalBudget - clamped

      if (currentOtherTotal <= 0) {
        const split = Math.floor(remainder / 2)
        return {
          ...prev,
          [key]: clamped,
          [others[0]]: split,
          [others[1]]: remainder - split,
        }
      }

      const ratioA = prev[others[0]] / currentOtherTotal
      const otherA = Math.round(remainder * ratioA)
      const otherB = remainder - otherA

      return {
        ...prev,
        [key]: clamped,
        [others[0]]: otherA,
        [others[1]]: otherB,
      }
    })
  }

  const result = useMemo(
    () =>
      roiCalculator({
        strategyA: allocations.strategyA,
        strategyB: allocations.strategyB,
        strategyC: allocations.strategyC,
        marketMultiplier: defaultRoiInputs.marketMultiplier,
        safetyMultiplier: defaultRoiInputs.safetyMultiplier,
        speedMultiplier: defaultRoiInputs.speedMultiplier,
      }),
    [allocations],
  )

  const remaining = totalBudget - (allocations.strategyA + allocations.strategyB + allocations.strategyC)
  const hasChartData = result.points && result.points.length > 0

  return (
    <section className="space-y-4">
      <Card>
        <h2 className="font-display text-lg mb-1">Budget / ROI Simulator</h2>
        <p className="text-sm text-ink-secondary mb-4">
          Allocate exactly ₹500M across the three strategies and project cumulative 5-year returns.
        </p>
        <div className="grid md:grid-cols-3 gap-4">
          <div>
            <div className="label">Strategy A allocation</div>
            <input type="range" min={0} max={500} step={5} value={allocations.strategyA} onChange={(e) => setAllocation('strategyA', Number(e.target.value))} />
            <div className="text-xs font-mono text-ink-secondary">₹{allocations.strategyA}M</div>
          </div>
          <div>
            <div className="label">Strategy B allocation</div>
            <input type="range" min={0} max={500} step={5} value={allocations.strategyB} onChange={(e) => setAllocation('strategyB', Number(e.target.value))} />
            <div className="text-xs font-mono text-ink-secondary">₹{allocations.strategyB}M</div>
          </div>
          <div>
            <div className="label">Strategy C allocation</div>
            <input type="range" min={0} max={500} step={5} value={allocations.strategyC} onChange={(e) => setAllocation('strategyC', Number(e.target.value))} />
            <div className="text-xs font-mono text-ink-secondary">₹{allocations.strategyC}M</div>
          </div>
        </div>
        <div className="mt-3 text-sm text-ink-secondary">
          Total allocated: <span className="font-semibold text-ink-primary">₹{result.totalInvested.toFixed(0)}M</span>
          {' • '}
          Unallocated: <span className="font-semibold text-ink-primary">₹{remaining}M</span>
        </div>
      </Card>

      <Card>
        <h3 className="font-display text-base mb-3">5-Year Cumulative Return Projection</h3>
        {!hasChartData ? (
          <div className="h-[300px] flex items-center justify-center text-ink-secondary">No data available</div>
        ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={result.points} margin={{ top: 10, right: 20, left: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
            <XAxis dataKey="year" label={{ value: 'Year', position: 'insideBottom', offset: -2 }} stroke="var(--ink-secondary)" />
            <YAxis label={{ value: 'Cumulative Return (₹M)', angle: -90, position: 'insideLeft' }} stroke="var(--ink-secondary)" />
            <Tooltip formatter={(value: number) => `₹${Number(value).toFixed(1)}M`} />
            <Legend verticalAlign="top" height={28} />
            <Line type="monotone" dataKey="strategyA" name="Strategy A" stroke="#22c55e" strokeWidth={2} dot />
            <Line type="monotone" dataKey="strategyB" name="Strategy B" stroke="#f59e0b" strokeWidth={2} dot />
            <Line type="monotone" dataKey="strategyC" name="Strategy C" stroke="#3b82f6" strokeWidth={2} dot />
            <Line type="monotone" dataKey="total" name="Total" stroke="#a78bfa" strokeWidth={3} dot={false} />
          </LineChart>
        </ResponsiveContainer>
        )}
      </Card>

      <div className="grid sm:grid-cols-3 gap-3">
        <div className="card-p">
          <div className="text-ink-secondary text-sm">Total Invested</div>
          <div className="text-2xl font-semibold mt-1">₹{result.totalInvested.toFixed(0)}M</div>
        </div>
        <div className="card-p">
          <div className="text-ink-secondary text-sm">Projected 5Y Return</div>
          <div className="text-2xl font-semibold mt-1">₹{result.projectedFiveYearReturn.toFixed(1)}M</div>
        </div>
        <div className="card-p">
          <div className="text-ink-secondary text-sm">IRR Estimate</div>
          <div className="text-2xl font-semibold mt-1">{result.irrEstimate.toFixed(2)}%</div>
        </div>
      </div>
    </section>
  )
}
