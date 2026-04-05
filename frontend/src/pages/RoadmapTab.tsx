import { useEffect, useMemo, useState } from 'react'
import { Card, Typography } from 'antd'
import { api } from '@/services/api'

export function RoadmapTab() {
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [filterYear, setFilterYear] = useState(0)

  useEffect(() => {
    const run = async () => {
      try {
        setError(null)
        const res = await api.roadmapData()
        setData(res)
      } catch {
        setError('Using fallback roadmap data.')
        setData({
          strategy: 'Strategy A - AI-Driven Drug Discovery Platform',
          total_budget_m: 500,
          phases: [
            { name: 'Foundation', years: 'Y1', color: '#4DA6FF', budget_m: 85 },
            { name: 'Validation', years: 'Y2', color: '#00C896', budget_m: 75 },
            { name: 'Expansion', years: 'Y3', color: '#7F77DD', budget_m: 115 },
            { name: 'Clinical Scale', years: 'Y4', color: '#F5A623', budget_m: 135 },
            { name: 'Harvest', years: 'Y5', color: '#00C896', budget_m: 90 },
          ],
          milestones: [
            { id: 'M01', year: 1, quarter: 'Q1', phase: 'Foundation', category: 'technology', title: 'AI platform v1.0 launch', description: 'Deploy target ID, lead generation and ADMET stack.', budget_m: 40, kpi: 'Prediction latency under 200ms' },
            { id: 'M02', year: 1, quarter: 'Q2', phase: 'Foundation', category: 'talent', title: 'Hire 80 ML scientists', description: 'Build team across chemistry, ML and regulatory science.', budget_m: 25, kpi: 'Team fully staffed' },
            { id: 'M03', year: 1, quarter: 'Q3', phase: 'Foundation', category: 'data', title: 'ChEMBL integration', description: 'Integrate 1M+ records and retrain core models.', budget_m: 15, kpi: 'AUC >= 0.88' },
            { id: 'M04', year: 1, quarter: 'Q4', phase: 'Foundation', category: 'commercial', title: 'First licensing deal', description: 'Sign first non-competing pharma partnership.', budget_m: 5, kpi: 'Deal signed' },
            { id: 'M05', year: 2, quarter: 'Q1', phase: 'Validation', category: 'pipeline', title: '3 IND candidates', description: 'Generate first three IND-ready candidates.', budget_m: 30, kpi: '3 candidates pass ADMET gate' },
            { id: 'M06', year: 2, quarter: 'Q2', phase: 'Validation', category: 'clinical', title: 'Phase 1 trial start', description: 'Initiate first AI-derived Phase 1 study.', budget_m: 40, kpi: 'First patient dosed' },
            { id: 'M07', year: 2, quarter: 'Q4', phase: 'Validation', category: 'commercial', title: 'Licensing deal #2', description: 'Onboard second enterprise partner.', budget_m: 5, kpi: '2 recurring partners' },
            { id: 'M08', year: 3, quarter: 'Q1', phase: 'Expansion', category: 'pipeline', title: 'Pipeline 8-12 programs', description: 'Scale across three therapeutic areas.', budget_m: 45, kpi: '8 active programs' },
            { id: 'M09', year: 3, quarter: 'Q2', phase: 'Expansion', category: 'financial', title: 'Break-even licensing', description: 'Licensing revenue covers platform OPEX.', budget_m: 10, kpi: 'Revenue >= OPEX' },
            { id: 'M10', year: 3, quarter: 'Q3', phase: 'Expansion', category: 'commercial', title: 'Strategic acquisition', description: 'Acquire data-rich AI biotech team.', budget_m: 60, kpi: 'Acquisition closed' },
            { id: 'M11', year: 4, quarter: 'Q1', phase: 'Clinical Scale', category: 'clinical', title: 'Phase 2 readout', description: 'Read out first efficacy results.', budget_m: 55, kpi: 'Endpoint achieved or adaptively expanded' },
            { id: 'M12', year: 4, quarter: 'Q3', phase: 'Clinical Scale', category: 'technology', title: 'GNN deployment', description: 'Upgrade to GNN core inference engine.', budget_m: 20, kpi: 'AUC >= 0.92' },
            { id: 'M13', year: 4, quarter: 'Q4', phase: 'Clinical Scale', category: 'financial', title: 'Platform ARR $80M', description: 'Reach 4+ active licensing partners.', budget_m: 0, kpi: 'ARR >= $80M' },
            { id: 'M14', year: 5, quarter: 'Q1', phase: 'Harvest', category: 'clinical', title: 'First NDA submission', description: 'Submit first NDA package with AI evidence.', budget_m: 30, kpi: 'NDA accepted for review' },
            { id: 'M15', year: 5, quarter: 'Q3', phase: 'Harvest', category: 'financial', title: 'Platform ARR $120M', description: 'Reach 6+ partner ecosystem scale.', budget_m: 0, kpi: 'ARR >= $120M' },
            { id: 'M16', year: 5, quarter: 'Q4', phase: 'Harvest', category: 'pipeline', title: '20-program pipeline', description: 'Operate 20 active programs and second NDA.', budget_m: 40, kpi: '20 active programs and 2 NDAs' },
          ],
        })
      }
    }
    run()
  }, [])

  const milestones = useMemo(() => {
    if (!data?.milestones) return []
    if (filterYear === 0) return data.milestones
    return data.milestones.filter((item: any) => item.year === filterYear)
  }, [data, filterYear])

  return (
    <section className="space-y-4">
      <Card>
        <Typography.Title level={4} style={{ marginBottom: 8 }}>Strategy A Milestone Gantt (Year 1-5)</Typography.Title>
        <Typography.Paragraph style={{ marginBottom: 0 }}>
          Track NexaClinIQ execution from platform build through NDA submission, with milestones color-coded by phase.
        </Typography.Paragraph>
      </Card>

      {error ? <div className="text-sm text-ink-secondary">{error}</div> : null}

      <div className="grid md:grid-cols-5 gap-3">
        {(data?.phases || []).map((phase: any) => (
          <div key={phase.name} className="card-p" style={{ borderColor: `${phase.color}44` }}>
            <div className="text-xs uppercase tracking-[0.12em] text-ink-secondary">{phase.years}</div>
            <div className="text-sm font-semibold" style={{ color: phase.color }}>{phase.name}</div>
            <div className="text-sm text-ink-secondary">${phase.budget_m}M</div>
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        {[0, 1, 2, 3, 4, 5].map((year) => (
          <button
            key={year}
            type="button"
            className="btn-ghost"
            style={{ borderColor: filterYear === year ? '#00C896' : 'rgba(0,200,150,0.2)', color: filterYear === year ? '#00C896' : undefined }}
            onClick={() => setFilterYear(year)}
          >
            {year === 0 ? 'All years' : `Year ${year}`}
          </button>
        ))}
      </div>

      <Card>
        <h3 className="font-display text-base mb-4">Timeline</h3>
        <div className="space-y-4 border-l-2 border-[#2563EB] pl-4">
          {milestones.length === 0 ? (
            <div className="text-sm text-ink-secondary">No milestones available.</div>
          ) : (
            milestones.map((milestone: any) => (
              <div key={milestone.id} className="grid grid-cols-[120px,1fr] gap-4">
                <div className="text-[13px] text-ink-secondary">Y{milestone.year} {milestone.quarter}</div>
                <div>
                  <div className="text-[14px] font-medium text-ink-primary">{milestone.title}</div>
                  <div className="text-[13px] text-ink-secondary">{milestone.description}</div>
                  <div className="text-[12px] text-[#00C896] mt-1">KPI: {milestone.kpi}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
    </section>
  )
}
