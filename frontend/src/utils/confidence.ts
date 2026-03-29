export function getConfidenceLabel(ciWidth: number): {
  label: 'High confidence' | 'Medium confidence' | 'Low confidence'
  color: string
  description: string
  colorHex: string
} {
  if (ciWidth < 0.1) {
    return {
      label: 'High confidence',
      color: 'green',
      colorHex: '#166534',
      description: 'The model has strong certainty in this prediction.',
    }
  }
  if (ciWidth < 0.25) {
    return {
      label: 'Medium confidence',
      color: 'yellow',
      colorHex: '#92400e',
      description: 'Moderate uncertainty — consider additional validation.',
    }
  }
  return {
    label: 'Low confidence',
    color: 'red',
    colorHex: '#991b1b',
    description: 'High uncertainty — this prediction should be treated as indicative only.',
  }
}

/**
 * Utility to calculate confidence interval width from bounds.
 */
export function calculateCIWidth(lower: number, upper: number): number {
  return upper - lower
}

/**
 * Utility to determine if a confidence interval is wide (uncertain).
 */
export function isWideCI(ciWidth: number): boolean {
  return ciWidth > 0.25
}

/**
 * Utility to assess confidence level as severity for UI colors.
 */
export function getConfidenceSeverity(ciWidth: number): 'success' | 'warning' | 'error' {
  if (ciWidth < 0.1) return 'success'
  if (ciWidth < 0.25) return 'warning'
  return 'error'
}
