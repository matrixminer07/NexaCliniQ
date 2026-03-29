interface PhaseBarProps {
  label: string
  value: number
}

export function PhaseBar({ label, value }: PhaseBarProps) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-ink-secondary">
        <span>{label}</span>
        <span className="font-mono">{value.toFixed(1)}%</span>
      </div>
      <div className="h-2 rounded-full bg-surface-1 overflow-hidden">
        <div className="h-full bg-brand transition-all duration-300" style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  )
}
