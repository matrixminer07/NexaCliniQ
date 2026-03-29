import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer } from 'recharts'
import { useAppStore } from '@/store'

export function CompareTab() {
  const a = useAppStore((s) => s.featuresA)
  const b = useAppStore((s) => s.featuresB)
  const setFeatureB = useAppStore((s) => s.setFeatureB)

  const data = [
    { feature: 'Toxicity', A: a.toxicity, B: b.toxicity },
    { feature: 'Bioavail', A: a.bioavailability, B: b.bioavailability },
    { feature: 'Solubility', A: a.solubility, B: b.solubility },
    { feature: 'Binding', A: a.binding, B: b.binding },
    { feature: 'MolWeight', A: a.molecular_weight, B: b.molecular_weight },
  ]

  if (!data || data.length === 0) {
    return <div className="card-p text-center text-ink-secondary">No data available</div>
  }

  return (
    <section className="grid lg:grid-cols-2 gap-4">
      <div className="card-p space-y-2">
        <h2 className="font-display text-lg">Compound B Controls</h2>
        {(Object.keys(b) as Array<keyof typeof b>).map((key) => (
          <div key={key}>
            <div className="text-xs text-ink-secondary mb-1">{key}</div>
            <input type="range" min={0} max={1} step={0.01} value={b[key]} style={{ ['--val' as string]: `${b[key] * 100}%` }} onChange={(e) => setFeatureB(key, Number(e.target.value))} />
          </div>
        ))}
      </div>
      <div className="card-p">
        <h2 className="font-display text-lg mb-2">A vs B Radar</h2>
        <ResponsiveContainer width="100%" height={300}>
          <RadarChart data={data}>
            <PolarGrid stroke="rgba(0,200,150,0.2)" />
            <PolarAngleAxis dataKey="feature" stroke="var(--ink-secondary)" />
            <Radar name="A" dataKey="A" stroke="var(--state-pass)" fill="rgba(0,200,150,0.2)" fillOpacity={0.6} />
            <Radar name="B" dataKey="B" stroke="var(--state-info)" fill="rgba(77,166,255,0.18)" fillOpacity={0.6} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
