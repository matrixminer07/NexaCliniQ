import { useEffect, useState } from 'react'
import { Alert, Card, Typography } from 'antd'
import { api } from '@/services/api'
import type { RoadmapPhase } from '@/types'

export function RoadmapTab() {
  const [roadmap, setRoadmap] = useState<RoadmapPhase[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const run = async () => {
      try {
        setError(null)
        const res = await api.roadmap()
        setRoadmap(res.roadmap || [])
      } catch {
        setError('Roadmap data is currently unavailable.')
        setRoadmap([])
      }
    }
    run()
  }, [])

  return (
    <section className="space-y-4">
      <Card>
        <Typography.Title level={4} style={{ marginBottom: 8 }}>Strategy A Milestone Gantt (Year 1-5)</Typography.Title>
        <Typography.Paragraph style={{ marginBottom: 0 }}>
          Track NexaClinIQ execution from platform build through NDA submission, with milestones color-coded by phase.
        </Typography.Paragraph>
      </Card>

      {error ? <Alert type="warning" message={error} showIcon /> : null}

      <Card>
        <h3 className="font-display text-base mb-4">Timeline</h3>
        <div className="space-y-4 border-l-2 border-[#2563EB] pl-4">
          {roadmap.length === 0 ? (
            <div className="text-sm text-ink-secondary">No milestones available.</div>
          ) : (
            roadmap.map((milestone) => (
              <div key={milestone.phase} className="grid grid-cols-[120px,1fr] gap-4">
                <div className="text-[13px] text-ink-secondary">{milestone.window}</div>
                <div>
                  <div className="text-[14px] font-medium text-ink-primary">{milestone.phase}</div>
                  <div className="text-[14px] text-ink-secondary">{milestone.focus}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
    </section>
  )
}
