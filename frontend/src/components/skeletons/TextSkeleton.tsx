type TextSkeletonProps = {
  lines?: number
}

const widths = ['100%', '85%', '92%', '70%']

export function TextSkeleton({ lines = 3 }: TextSkeletonProps) {
  return (
    <div className="space-y-2" aria-hidden="true">
      {Array.from({ length: lines }).map((_, idx) => (
        <div
          key={idx}
          className="skeleton-pulse"
          style={{
            width: widths[idx % widths.length],
            height: 14,
            borderRadius: 4,
            background: 'var(--color-background-secondary, #e5e7eb)',
          }}
        />
      ))}
    </div>
  )
}
