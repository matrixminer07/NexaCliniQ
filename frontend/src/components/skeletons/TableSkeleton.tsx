type TableSkeletonProps = {
  rows?: number
}

const widths = ['40%', '25%', '15%', '20%']

export function TableSkeleton({ rows = 6 }: TableSkeletonProps) {
  return (
    <div className="space-y-3" aria-hidden="true">
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div key={rowIdx} className="grid grid-cols-4 gap-3">
          {widths.map((width, colIdx) => (
            <div
              key={`${rowIdx}-${colIdx}`}
              className="skeleton-pulse"
              style={{
                width,
                height: 14,
                borderRadius: 4,
                background: 'var(--color-background-secondary, #e5e7eb)',
              }}
            />
          ))}
        </div>
      ))}
    </div>
  )
}
