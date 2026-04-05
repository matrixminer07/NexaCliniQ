type TooltipPayloadItem = {
  color?: string
  name?: string
  value?: number | string
}

type DarkTooltipProps = {
  active?: boolean
  payload?: TooltipPayloadItem[]
  label?: string | number
  currency?: string
  suffix?: string
  formatter?: (value: number | string, item: TooltipPayloadItem) => string
}

export function DarkTooltip({ active, payload, label, currency = '', suffix = '', formatter }: DarkTooltipProps) {
  if (!active || !payload?.length) return null

  return (
    <div
      style={{
        background: '#1C2B28',
        border: '1px solid rgba(0,200,150,0.25)',
        borderRadius: 10,
        padding: '10px 14px',
        fontSize: 12,
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      }}
    >
      {label !== undefined ? (
        <p style={{ color: '#8BA89F', marginBottom: 6, fontSize: 11 }}>{String(label)}</p>
      ) : null}
      {payload.map((item, index) => {
        const raw = item.value ?? ''
        const rendered = formatter
          ? formatter(raw, item)
          : `${currency}${typeof raw === 'number' ? raw.toLocaleString() : raw}${suffix}`

        return (
          <p
            key={`${item.name || 'series'}-${index}`}
            style={{
              color: item.color || '#E8F5F2',
              fontWeight: 500,
              marginBottom: 2,
              fontFamily: 'IBM Plex Mono',
            }}
          >
            {item.name || 'Value'}: {rendered}
          </p>
        )
      })}
    </div>
  )
}
