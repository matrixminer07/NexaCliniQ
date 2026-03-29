import clsx from 'clsx'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { useAppStore } from '@/store'
import type { FeatureSet, TabKey, TherapeuticArea } from '@/types'

const featureKeys: Array<keyof FeatureSet> = ['toxicity', 'bioavailability', 'solubility', 'binding', 'molecular_weight']

const tabs: Array<{ key: TabKey; label: string }> = [
  { key: 'compare', label: 'Compare' },
  { key: 'roadmap', label: 'Roadmap' },
  { key: 'financial', label: 'Budget' },
  { key: 'regulatory', label: 'Regulatory' },
  { key: 'partnerships', label: 'Partners' },
  { key: 'competition', label: 'Market' },

  { key: 'predict', label: 'Predict' },
  { key: 'strategy', label: 'Strategy Compare' },
  { key: 'executive-summary', label: 'Executive Summary' },
  { key: 'market-sizing', label: 'Market Sizing' },
  { key: 'risk-register', label: 'Risk Register' },
  { key: 'financial-detail', label: 'Financial Detail' },
  { key: 'pipeline', label: 'Pipeline' },
  { key: 'history', label: 'History' },
  { key: 'scenarios', label: 'Scenarios' },
]

export function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()
  const isAdmin = String(user?.role ?? '').toLowerCase() === 'admin'
  const {
    currentTab,
    setCurrentTab,
    sidebarOpen,
    setSidebarOpen,
    compoundName,
    setCompoundName,
    featuresA,
    setFeatureA,
    resetA,
    smiles,
    setSmiles,
    targetProbability,
    setTargetProbability,
    therapeuticArea,
    setTherapeuticArea,
  } = useAppStore()

  return (
    <aside className={clsx('fixed md:static z-20 h-screen w-[260px] bg-surface-1 border-r border-[rgba(0,200,150,0.12)] p-4 overflow-y-auto transition-transform duration-200', sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0')}>
      <div className="space-y-2">
        <img
          src="/logo.png"
          alt="NexaClinIQ"
          className="h-12 w-auto object-contain"
        />
        <p className="text-xs text-ink-secondary">GenAI Clinical Intelligence Research</p>
      </div>

      <div className="divider my-4" />
      <div className="space-y-3">
        <div className="label">Compound</div>
        <div className="flex gap-2">
          <input className="input" value={compoundName} onChange={(e) => setCompoundName(e.target.value)} />
          <button className="btn-ghost" onClick={resetA}>↻</button>
        </div>
      </div>

      <div className="divider my-4" />
      <div className="space-y-3">
        <div className="label">Molecular Properties</div>
        {featureKeys.map((key) => {
          const value = featuresA[key]
          return (
            <div key={key} className="space-y-1">
              <div className="flex justify-between text-xs text-ink-secondary">
                <span>{key.replace('_', ' ')}</span>
                <span className="font-mono">{value.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={value}
                style={{ ['--val' as string]: `${value * 100}%` }}
                onChange={(e) => setFeatureA(key, Number(e.target.value))}
              />
            </div>
          )
        })}
      </div>

      <div className="divider my-4" />
      <div className="space-y-2">
        <div className="label">SMILES Input</div>
        <input className="input font-mono" placeholder="Paste SMILES..." value={smiles} onChange={(e) => setSmiles(e.target.value)} />
      </div>

      <div className="space-y-2 mt-4">
        <div className="label">Target for counterfactual</div>
        <input type="range" min={0.5} max={0.95} step={0.01} value={targetProbability} style={{ ['--val' as string]: `${targetProbability * 100}%` }} onChange={(e) => setTargetProbability(Number(e.target.value))} />
        <div className="text-xs font-mono text-ink-secondary">{(targetProbability * 100).toFixed(0)}%</div>
      </div>

      <div className="space-y-2 mt-4">
        <div className="label">Therapeutic Area</div>
        <select className="input" value={therapeuticArea} onChange={(e) => setTherapeuticArea(e.target.value as TherapeuticArea)}>
          <option value="oncology">Oncology</option>
          <option value="cns">CNS</option>
          <option value="rare">Rare Disease</option>
          <option value="cardiology">Cardiovascular</option>
          <option value="infectious">Infectious Disease</option>
          <option value="metabolic">Metabolic Disease</option>
        </select>
      </div>

      <div className="divider my-4" />
      <div className="space-y-2">
        <div className="label">Navigation</div>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            className={clsx('w-full text-left px-2 py-1 rounded-md text-sm', currentTab === tab.key ? 'text-brand bg-brand-subtle font-medium' : 'text-ink-secondary hover:text-ink-primary')}
            onClick={() => {
              setCurrentTab(tab.key)
              setSidebarOpen(false)
            }}
          >
            {currentTab === tab.key ? '◉ ' : '○ '}{tab.label}
          </button>
        ))}
      </div>

      {isAdmin ? (
        <>
          <div className="divider my-4" />
          <div className="space-y-2">
            <div className="label">Admin</div>
            <button
              className={clsx(
                'w-full text-left px-2 py-1 rounded-md text-sm',
                location.pathname.startsWith('/admin') ? 'text-brand bg-brand-subtle font-medium' : 'text-ink-secondary hover:text-ink-primary'
              )}
              onClick={() => {
                navigate('/admin-site')
                setSidebarOpen(false)
              }}
            >
              {location.pathname.startsWith('/admin') ? '◉ ' : '○ '}Control Center
            </button>
          </div>
        </>
      ) : null}
    </aside>
  )
}
