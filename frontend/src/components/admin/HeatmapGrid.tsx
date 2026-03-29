type HeatCell = { day: string; hour: string; count: number }

type HeatmapGridProps = {
  cells: HeatCell[]
}

function mix(a: number, b: number, t: number) {
  return Math.round(a + (b - a) * t)
}

function blueRamp(intensity: number) {
  const t = Math.max(0, Math.min(1, intensity))
  const r = mix(238, 29, t)
  const g = mix(242, 78, t)
  const b = mix(255, 216, t)
  return `rgb(${r}, ${g}, ${b})`
}

export function HeatmapGrid({ cells }: HeatmapGridProps) {
  const maxCount = Math.max(...cells.map((c) => c.count), 1)
  const grouped = new Map<string, HeatCell[]>()
  for (const cell of cells) {
    const row = grouped.get(cell.day) ?? []
    row.push(cell)
    grouped.set(cell.day, row)
  }

  return (
    <div className="space-y-2">
      {[...grouped.entries()].map(([day, dayCells]) => (
        <div key={day} className="flex items-center gap-2">
          <div className="w-12 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            {day}
          </div>
          <div className="flex gap-[2px]">
            {dayCells.map((cell) => {
              const intensity = cell.count / maxCount
              return (
                <div
                  key={`${cell.day}-${cell.hour}`}
                  title={`${cell.day} ${cell.hour}:00 - ${cell.count} requests`}
                  className="h-5 w-6 rounded-[2px]"
                  style={{ background: blueRamp(intensity) }}
                />
              )
            })}
          </div>
        </div>
      ))}
      <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
        Color scale: low to high activity
      </p>
    </div>
  )
}
