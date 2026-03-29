export function PipelineTab() {
  return (
    <section className="space-y-4">
      <div className="card-p">
        <h2 className="font-display text-lg">AI Accelerated Pipeline</h2>
        <p className="text-ink-secondary text-sm">Traditional and AI-assisted drug development timelines.</p>
      </div>
      <div className="card-p space-y-4">
        <div>
          <div className="label">Traditional</div>
          <div className="h-4 rounded bg-[rgba(255,107,107,0.2)] w-full" />
          <div className="text-xs text-ink-secondary mt-1">8.9 years</div>
        </div>
        <div>
          <div className="label">AI Accelerated</div>
          <div className="h-4 rounded bg-[rgba(0,200,150,0.3)] w-2/3 animate-fade-up" />
          <div className="text-xs text-ink-secondary mt-1">5.5 years</div>
        </div>
        <div className="metric-value">3.4 years saved</div>
      </div>
    </section>
  )
}
