export function ChartSkeleton() {
  return (
    <div
      className="skeleton-pulse"
      style={{
        width: '100%',
        height: 'clamp(200px, 38vw, 300px)',
        borderRadius: 8,
        background: 'var(--color-background-secondary, #e5e7eb)',
      }}
      aria-hidden="true"
    />
  )
}
