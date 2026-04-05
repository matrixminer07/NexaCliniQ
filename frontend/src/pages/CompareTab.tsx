import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer } from 'recharts'
import { useAppStore } from '@/store'
import type { FeatureSet, TherapeuticArea } from '@/types'

const featureKeys: Array<keyof FeatureSet> = ['toxicity', 'bioavailability', 'solubility', 'binding', 'molecular_weight']

const featureLabels: Record<keyof FeatureSet, string> = {
  toxicity: 'Toxicity',
  bioavailability: 'Bioavailability',
  solubility: 'Solubility',
  binding: 'Binding affinity',
  molecular_weight: 'Molecular weight',
}

const therapeuticOptions: Array<{ value: TherapeuticArea; label: string }> = [
  { value: 'oncology', label: 'Oncology' },
  { value: 'cns', label: 'CNS' },
  { value: 'rare', label: 'Rare disease' },
  { value: 'cardiology', label: 'Cardiology' },
  { value: 'infectious', label: 'Infectious' },
  { value: 'metabolic', label: 'Metabolic' },
]

export function CompareTab() {
  const a = useAppStore((s) => s.featuresA)
  const b = useAppStore((s) => s.featuresB)
  const setFeatureA = useAppStore((s) => s.setFeatureA)
  const setFeatureB = useAppStore((s) => s.setFeatureB)
  const compoundName = useAppStore((s) => s.compoundName)
  const setCompoundName = useAppStore((s) => s.setCompoundName)
  const therapeuticArea = useAppStore((s) => s.therapeuticArea)
  const setTherapeuticArea = useAppStore((s) => s.setTherapeuticArea)

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
    <section className="space-y-4">
      <div className="card-p">
        <h2 className="font-display text-lg mb-3">Compare Compounds</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-[11px] font-medium text-ink-secondary" htmlFor="compareCompoundName">Compound name</label>
            <input
              id="compareCompoundName"
              className="input h-9 text-sm"
              value={compoundName}
              onChange={(event) => setCompoundName(event.target.value)}
            />
          </div>
          <div className="space-y-1">
            <label className="text-[11px] font-medium text-ink-secondary" htmlFor="compareTherapeuticArea">Therapeutic area</label>
            <select
              id="compareTherapeuticArea"
              className="input h-9 text-sm"
              value={therapeuticArea}
              onChange={(event) => setTherapeuticArea(event.target.value as TherapeuticArea)}
            >
              {therapeuticOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="grid xl:grid-cols-2 gap-4">
        <div className="card-p space-y-2">
          <h3 className="font-display text-base">Compound A Profile</h3>
          {featureKeys.map((key) => (
            <div key={`A-${key}`} className="space-y-1">
              <div className="flex items-center justify-between text-xs text-ink-secondary">
                <label>{featureLabels[key]}</label>
                <span className="rounded border border-line px-1.5 py-0.5 text-[10px] font-mono">{a[key].toFixed(2)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={a[key]}
                style={{ ['--val' as string]: `${a[key] * 100}%` }}
                onChange={(e) => setFeatureA(key, Number(e.target.value))}
              />
            </div>
          ))}
        </div>

        <div className="card-p space-y-2">
          <h3 className="font-display text-base">Compound B Profile</h3>
          {featureKeys.map((key) => (
            <div key={`B-${key}`} className="space-y-1">
              <div className="flex items-center justify-between text-xs text-ink-secondary">
                <label>{featureLabels[key]}</label>
                <span className="rounded border border-line px-1.5 py-0.5 text-[10px] font-mono">{b[key].toFixed(2)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={b[key]}
                style={{ ['--val' as string]: `${b[key] * 100}%` }}
                onChange={(e) => setFeatureB(key, Number(e.target.value))}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="card-p">
        <h3 className="font-display text-lg mb-2">A vs B Radar</h3>
        <ResponsiveContainer width="100%" height={360}>
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
