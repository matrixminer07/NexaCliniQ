import { useEffect, useMemo, useState } from 'react'
import { api } from '@/services/api'
import { downloadCsv } from '@/utils/export'

type RiskRow = {
  id: string
  title: string
  category: string
  severity: 'high' | 'medium' | 'low'
  description: string
  mitigation: string
  status: string
  score: number
}

const SEV_COLORS: Record<RiskRow['severity'], string> = {
  high: '#FF6B6B',
  medium: '#F5A623',
  low: '#00C896',
}
const SEV_BG: Record<RiskRow['severity'], string> = {
  high: 'rgba(255,107,107,0.1)',
  medium: 'rgba(245,166,35,0.1)',
  low: 'rgba(0,200,150,0.1)',
}

const FALLBACK_RISKS: RiskRow[] = [
  { id: 'REG-001', category: 'Regulatory', severity: 'high', title: 'FDA AI/ML framework uncertainty', description: 'FDA evolving guidance may extend AI compound approval by 18-24 months.', mitigation: 'Engage FDA pre-submission and build regulatory science team.', status: 'active', score: 16 },
  { id: 'TECH-001', category: 'Technical', severity: 'high', title: 'AI model data quality dependency', description: 'Synthetic-heavy training may not generalize to real libraries.', mitigation: 'Integrate ChEMBL scale data and deploy drift monitoring.', status: 'in_progress', score: 16 },
  { id: 'REG-002', category: 'Regulatory', severity: 'high', title: 'EU AI Act high-risk classification', description: 'EU controls require conformity assessment and complete audit trail.', mitigation: 'Implement Article 12-aligned audit and HITL controls.', status: 'monitoring', score: 15 },
  { id: 'FIN-001', category: 'Financial', severity: 'medium', title: 'R&D capital burn rate', description: 'High upfront spend can stress runway before meaningful revenue.', mitigation: 'Phase spend and accelerate platform licensing.', status: 'monitoring', score: 12 },
  { id: 'MKT-001', category: 'Market', severity: 'medium', title: 'Big pharma AI build-vs-buy', description: 'In-house AI investment by incumbents can reduce licensing demand.', mitigation: 'Focus on specialized indications and data moat.', status: 'monitoring', score: 12 },
  { id: 'OPS-001', category: 'Operational', severity: 'medium', title: 'ML talent acquisition gap', description: 'Competition for bio-ML talent stretches hiring cycle.', mitigation: 'Academic partnerships and remote-first hiring.', status: 'active', score: 12 },
  { id: 'TECH-002', category: 'Technical', severity: 'medium', title: 'AI model obsolescence', description: 'Rapid model evolution can age static architectures quickly.', mitigation: 'Maintain modular architecture and GNN migration track.', status: 'planned', score: 9 },
  { id: 'MKT-002', category: 'Market', severity: 'medium', title: 'Competitor IP landscape', description: 'AI-generated molecule IP boundaries remain contested.', mitigation: 'File provisionals early and monitor patent filings.', status: 'active', score: 9 },
  { id: 'FIN-002', category: 'Financial', severity: 'low', title: 'Licensing concentration risk', description: 'Revenue concentration in 2-3 partners increases downside risk.', mitigation: 'Expand partner base and minimum payment clauses.', status: 'planned', score: 8 },
  { id: 'OPS-002', category: 'Operational', severity: 'low', title: 'Cloud HPC cost overrun', description: 'GPU-heavy workloads can exceed forecast spend without controls.', mitigation: 'Introduce spend guardrails and committed use plans.', status: 'planned', score: 6 },
]

export function RiskRegisterTab() {
  const [rows, setRows] = useState<RiskRow[]>(FALLBACK_RISKS)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all')
  const [expanded, setExpanded] = useState<string | null>(null)

  const load = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.riskRegisterData()
      const incoming = ((response as { risks?: RiskRow[] }).risks || FALLBACK_RISKS)
      setRows(incoming)
    } catch {
      setError('Using fallback risk register data.')
      setRows(FALLBACK_RISKS)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const summary = useMemo(
    () => ({
      total: rows.length,
      high: rows.filter((item) => item.severity === 'high').length,
      medium: rows.filter((item) => item.severity === 'medium').length,
      low: rows.filter((item) => item.severity === 'low').length,
    }),
    [rows],
  )

  const filtered = useMemo(
    () => (filter === 'all' ? rows : rows.filter((item) => item.severity === filter)),
    [filter, rows],
  )

  const exportRows = filtered.map((risk) => ({
    id: risk.id,
    category: risk.category,
    severity: risk.severity,
    title: risk.title,
    score: risk.score,
    status: risk.status,
  }))

  return (
    <section className="space-y-4">
      <div className="card-p">
        <div className="flex items-center justify-between gap-2">
          <h2 className="font-display text-lg">Risk Register</h2>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn-ghost"
              aria-label="Export risk register CSV"
              onClick={() => downloadCsv('risk-register.csv', exportRows)}
              disabled={loading || filtered.length === 0}
            >
              Export CSV
            </button>
            <button type="button" className="btn-ghost" aria-label="Refresh risk register" onClick={() => void load()}>
              ↻
            </button>
          </div>
        </div>
        <p className="text-sm text-ink-secondary">Strategic and operational risks with mitigation coverage.</p>
      </div>

      {error ? <div className="text-sm text-ink-secondary">{error}</div> : null}

      <div className="grid md:grid-cols-4 gap-3">
        {[
          { label: 'Total risks', value: summary.total, color: '#E8F5F2' },
          { label: 'High', value: summary.high, color: '#FF6B6B' },
          { label: 'Medium', value: summary.medium, color: '#F5A623' },
          { label: 'Low', value: summary.low, color: '#00C896' },
        ].map((item) => (
          <div key={item.label} className="card-p">
            <div className="text-xs uppercase tracking-[0.12em] text-ink-secondary">{item.label}</div>
            <div className="text-2xl font-semibold mt-1" style={{ color: item.color }}>{item.value}</div>
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        {(['all', 'high', 'medium', 'low'] as const).map((item) => (
          <button
            key={item}
            type="button"
            className="btn-ghost"
            style={{
              borderColor: filter === item ? '#00C896' : 'rgba(0,200,150,0.2)',
              color: filter === item ? '#00C896' : undefined,
            }}
            onClick={() => setFilter(item)}
          >
            {item === 'all' ? 'All risks' : `${item[0].toUpperCase()}${item.slice(1)}`}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {filtered.map((risk) => (
          <div
            key={risk.id}
            onClick={() => setExpanded(expanded === risk.id ? null : risk.id)}
            style={{
              background: '#162220',
              border: `1px solid ${SEV_COLORS[risk.severity]}25`,
              borderLeft: `3px solid ${SEV_COLORS[risk.severity]}`,
              borderRadius: '0 12px 12px 0',
              padding: '16px 20px',
              cursor: 'pointer',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#E8F5F2', marginBottom: 2 }}>{risk.title}</div>
                <div style={{ fontSize: 11, color: '#8BA89F' }}>{risk.category} · ID: {risk.id}</div>
              </div>
              <span
                style={{
                  padding: '3px 10px',
                  borderRadius: 20,
                  fontSize: 10,
                  fontWeight: 600,
                  background: SEV_BG[risk.severity],
                  color: SEV_COLORS[risk.severity],
                  textTransform: 'uppercase',
                }}
              >
                {risk.severity}
              </span>
            </div>
            {expanded === risk.id ? (
              <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid rgba(0,200,150,0.1)' }}>
                <p style={{ fontSize: 13, color: '#8BA89F', lineHeight: 1.6, marginBottom: 10 }}>{risk.description}</p>
                <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, color: '#506860', marginBottom: 4 }}>Mitigation</div>
                <p style={{ fontSize: 13, color: '#00C896', lineHeight: 1.5 }}>{risk.mitigation}</p>
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  )
}
