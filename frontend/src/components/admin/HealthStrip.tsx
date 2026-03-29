type HealthStripProps = {
  health: Record<string, unknown> | null
  lastCheckedLabel: string
}

function colorForStatus(value: unknown) {
  if (value === true || value === 'healthy' || value === 'ok') return 'var(--color-text-success)'
  if (value === 'degraded') return 'var(--color-text-warning)'
  return 'var(--color-text-danger)'
}

export function HealthStrip({ health, lastCheckedLabel }: HealthStripProps) {
  const features = (health?.features as Record<string, unknown> | undefined) ?? {}
  const services = [
    { key: 'database', name: 'Postgres' },
    { key: 'redis', name: 'Redis' },
    { key: 'model_loaded', name: 'Model' },
    { key: 'smiles', name: 'RDKit' },
    { key: 'gnn', name: 'GNN' },
  ]

  return (
    <div className="rounded-xl border p-4" style={{ background: 'var(--color-background-primary)', borderColor: 'var(--color-border-tertiary)' }}>
      <div className="flex flex-wrap items-center gap-4">
        {services.map((service) => {
          const value = service.key in features ? features[service.key] : health?.[service.key]
          return (
            <div key={service.key} className="flex items-center gap-2 text-sm">
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: colorForStatus(value) }} />
              <span style={{ color: 'var(--color-text-primary)' }}>{service.name}</span>
              <span style={{ color: 'var(--color-text-secondary)' }}>{String(value ?? 'unknown')}</span>
            </div>
          )
        })}
      </div>
      <p className="mt-2 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
        Last checked {lastCheckedLabel}
      </p>
    </div>
  )
}
