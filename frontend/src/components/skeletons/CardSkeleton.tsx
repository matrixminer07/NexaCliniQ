type CardSkeletonProps = {
  width?: string | number
  height?: string | number
}

export function CardSkeleton({ width = '100%', height = 120 }: CardSkeletonProps) {
  return (
    <div
      className="skeleton-pulse"
      style={{
        width,
        height,
        borderRadius: 8,
        background: 'var(--color-background-secondary, #e5e7eb)',
      }}
      aria-hidden="true"
    />
  )
}
