import React from 'react'
import './Skeleton.css'

export interface SkeletonProps {
  className?: string
  width?: string | number
  height?: string | number
}

/**
 * CardSkeleton — animated grey pulse block for loading states.
 */
export const CardSkeleton: React.FC<SkeletonProps & { count?: number }> = ({
  width = '100%',
  height = 120,
  className = '',
  count = 1,
}) => {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={`skeleton-card ${className}`}
          style={{
            width: typeof width === 'number' ? `${width}px` : width,
            height: typeof height === 'number' ? `${height}px` : height,
          }}
        />
      ))}
    </>
  )
}

/**
 * TextSkeleton — simulates paragraph lines of text.
 */
export const TextSkeleton: React.FC<SkeletonProps & { lines?: number }> = ({
  lines = 3,
  className = '',
}) => {
  return (
    <div className={`skeleton-text ${className}`}>
      {Array.from({ length: lines }).map((_, i) => {
        // Vary width of lines to look more natural
        const widths = ['100%', '95%', '80%', '85%']
        const width = widths[i % widths.length]
        return (
          <div
            key={i}
            className="skeleton-line"
            style={{ width, marginBottom: i < lines - 1 ? '12px' : '0' }}
          />
        )
      })}
    </div>
  )
}

/**
 * TableSkeleton — simulates table rows and columns.
 */
export const TableSkeleton: React.FC<{ rows?: number; columns?: number; className?: string }> = ({
  rows = 5,
  columns = 4,
  className = '',
}) => {
  return (
    <div className={`skeleton-table ${className}`}>
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div key={rowIdx} className="skeleton-table-row">
          {Array.from({ length: columns }).map((_, colIdx) => {
            // Vary column widths
            const widths = ['25%', '30%', '20%', '25%']
            const width = widths[colIdx % widths.length]
            return (
              <div
                key={colIdx}
                className="skeleton-table-cell"
                style={{ width, minWidth: '60px' }}
              />
            )
          })}
        </div>
      ))}
    </div>
  )
}

/**
 * ChartSkeleton — a rounded rect placeholder for charts.
 */
export const ChartSkeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = 300,
  className = '',
}) => {
  return (
    <div
      className={`skeleton-chart ${className}`}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
      }}
    />
  )
}

/**
 * BarChartSkeleton — multiple bars simulating a bar chart.
 */
export const BarChartSkeleton: React.FC<SkeletonProps & { bars?: number }> = ({
  bars = 5,
  height = 300,
  className = '',
}) => {
  const barHeights = ['34%', '52%', '79%', '61%', '43%', '70%', '57%', '38%']

  return (
    <div className={`skeleton-bar-chart ${className}`} style={{ height }}>
      {Array.from({ length: bars }).map((_, i) => (
        <div
          key={i}
          className="skeleton-bar"
          style={{
            height: barHeights[i % barHeights.length],
          }}
        />
      ))}
    </div>
  )
}
