import { ChartSkeleton } from '@/components/skeletons/ChartSkeleton'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts'

type CalibrationPoint = { predicted: number; actual: number }

type CalibrationChartProps = {
  points: CalibrationPoint[]
  loading: boolean
  error: string | null
}

function computeEce(points: CalibrationPoint[]) {
  if (!points.length) return 0
  const binSize = 0.1
  let ece = 0
  for (let b = 0; b < 10; b += 1) {
    const min = b * binSize
    const max = min + binSize
    const inBin = points.filter((point) => point.predicted >= min && point.predicted < max)
    if (!inBin.length) continue
    const acc = inBin.reduce((sum, point) => sum + point.actual, 0) / inBin.length
    const conf = inBin.reduce((sum, point) => sum + point.predicted, 0) / inBin.length
    ece += (inBin.length / points.length) * Math.abs(acc - conf)
  }
  return ece
}

export function CalibrationChart({ points, loading, error }: CalibrationChartProps) {
  if (loading) return <ChartSkeleton />
  if (error) return <div className="rounded-md border p-3 text-sm" style={{ borderColor: 'var(--color-border-tertiary)' }}>{error}</div>

  const ece = computeEce(points)

  return (
    <div className="rounded-xl border p-4" style={{ background: 'var(--color-background-primary)', borderColor: 'var(--color-border-tertiary)' }}>
      <h3 className="text-base font-medium">Prediction calibration</h3>
      <p className="mt-1 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
        ECE = sum (|B<sub>m</sub>|/n) x |acc(B<sub>m</sub>) - conf(B<sub>m</sub>)|
      </p>
      <p className="text-sm" style={{ color: 'var(--color-text-primary)' }}>Expected calibration error: {ece.toFixed(4)}</p>
      <div className="mt-3 h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart>
            <CartesianGrid stroke="rgba(0,0,0,0.08)" />
            <XAxis dataKey="predicted" type="number" domain={[0, 1]} />
            <YAxis dataKey="actual" type="number" domain={[0, 1]} />
            <Tooltip />
            <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="var(--color-text-secondary)" strokeDasharray="4 4" />
            <Scatter data={points} fill="var(--color-text-brand)" />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
