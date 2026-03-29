import { Card, Typography } from 'antd'
import { regulatoryPipelines } from '@/components/strategy/novacuraData'

export function RegulatoryTab() {
  const statusClass = {
    completed: 'bg-slate-500/30 border-slate-400/50 text-slate-200',
    active: 'bg-blue-500/20 border-blue-400/60 text-blue-200',
    projected: 'bg-transparent border-dashed border-white/40 text-ink-secondary',
  }

  return (
    <section className="space-y-4">
      <Card>
        <Typography.Title level={4} style={{ marginBottom: 8 }}>Regulatory Timeline</Typography.Title>
        <Typography.Paragraph style={{ marginBottom: 0 }}>
          Horizontal stage pipelines compare regulatory pathways and expected gates for each strategy.
        </Typography.Paragraph>
      </Card>

      <Card>
        <div className="space-y-5">
          {regulatoryPipelines.map((strategy) => (
            <div key={strategy.name} className="space-y-2">
              <div className="text-sm font-semibold text-ink-primary">{strategy.name}</div>
              <div className="overflow-x-auto">
                <div className="min-w-[920px] flex items-center gap-2">
                  {strategy.stages.map((stage, idx) => (
                    <div key={`${strategy.name}-${stage.label}`} className="flex items-center gap-2">
                      <div className={`px-3 py-2 rounded-full border text-xs whitespace-nowrap ${statusClass[stage.status]}`}>
                        <div className="font-semibold">{stage.label}</div>
                        <div>{stage.date}</div>
                      </div>
                      {idx < strategy.stages.length - 1 ? (
                        <div className="text-ink-secondary text-xs">→</div>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </section>
  )
}
