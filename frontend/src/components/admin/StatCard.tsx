type StatCardProps = {
  label: string
  value: string
  delta?: string
  deltaTone?: 'success' | 'warning' | 'danger'
  footer?: string
}

export function StatCard({ label, value, delta, deltaTone = 'success', footer }: StatCardProps) {
  const toneColor =
    deltaTone === 'success'
      ? 'var(--color-text-success)'
      : deltaTone === 'warning'
        ? 'var(--color-text-warning)'
        : 'var(--color-text-danger)'

  return (
    <div
      className="rounded-xl p-5"
      style={{
        background: 'var(--color-background-primary)',
        border: '0.5px solid var(--color-border-tertiary)',
      }}
    >
      <p className="text-xs uppercase" style={{ color: 'var(--color-text-secondary)', letterSpacing: '0.08em' }}>
        {label}
      </p>
      <p className="mt-2 text-[28px] font-medium" style={{ color: 'var(--color-text-primary)' }}>
        {value}
      </p>
      {delta ? (
        <span
          className="mt-2 inline-block rounded px-2 py-0.5 text-xs"
          style={{ background: 'var(--color-background-success)', color: toneColor }}
        >
          {delta}
        </span>
      ) : null}
      {footer ? (
        <p className="mt-2 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
          {footer}
        </p>
      ) : null}
    </div>
  )
}
