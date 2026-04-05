export function formatMillions(value: number | null | undefined, fractionDigits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A'
  const amount = Math.abs(Number(value))
  const prefix = Number(value) < 0 ? '-$' : '$'
  const formatted = amount.toLocaleString('en-US', {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })
  return `${prefix}${formatted}M`
}

export function formatMillionsWithLabel(value: number | null | undefined, fractionDigits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A'
  const amount = Math.abs(Number(value))
  const prefix = Number(value) < 0 ? '-$' : '$'
  const formatted = amount.toLocaleString('en-US', {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })
  return `${prefix}${formatted} million`
}
