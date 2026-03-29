/**
 * Types for SHAP contributions based on the model output structure.
 */
export interface ShapContribution {
  feature: string
  value: number
  direction: 'positive' | 'negative'
}

/**
 * Generate plain-English rationale from SHAP values and prediction score.
 */
export function generateRationale(
  shapBreakdown: Record<string, any> | undefined,
  score: number,
  compoundName?: string
): string {
  if (!shapBreakdown) {
    return `${compoundName || 'This compound'} has a success probability of ${(score * 100).toFixed(1)}%.`
  }

  // Extract top positive and negative contributors
  const contributions = extractTopContributions(shapBreakdown, 3)

  if (contributions.positive.length === 0 && contributions.negative.length === 0) {
    return `${compoundName || 'This compound'} has a success probability of ${(score * 100).toFixed(1)}% based on the analyzed features.`
  }

  const parts: string[] = []
  const prefix = `${compoundName || 'This compound'} scores ${(score * 100).toFixed(1)}% primarily due to`

  // Build reason from top contributors
  const reasons: string[] = []

  if (contributions.positive.length > 0) {
    const positiveFeatures = contributions.positive
      .slice(0, 2)
      .map((c) => formatFeatureName(c.feature))
      .join(' and ')
    reasons.push(`${positiveFeatures}`)
  }

  if (contributions.negative.length > 0) {
    const negativeFeatures = contributions.negative
      .slice(0, 2)
      .map((c) => formatFeatureName(c.feature))
      .join(' and ')
    if (reasons.length > 0) {
      reasons.push(`offset by poor ${negativeFeatures}`)
    } else {
      reasons.push(`concerns with ${negativeFeatures}`)
    }
  }

  return `${prefix} ${reasons.join(' ')}.`
}

/**
 * Extract top positive and negative SHAP contributions.
 */
function extractTopContributions(
  shapBreakdown: Record<string, any>,
  topN: number = 3
): { positive: ShapContribution[]; negative: ShapContribution[] } {
  const contributions: ShapContribution[] = []

  // Handle different possible SHAP output formats
  const contributions_array = shapBreakdown.contributions || shapBreakdown.values || []

  if (Array.isArray(contributions_array)) {
    for (const item of contributions_array) {
      if (typeof item === 'object' && item !== null && 'feature' in item && 'value' in item) {
        contributions.push({
          feature: item.feature,
          value: item.value,
          direction: (item.value ?? 0) > 0 ? 'positive' : 'negative',
        })
      }
    }
  } else if (typeof contributions_array === 'object') {
    for (const [key, value] of Object.entries(contributions_array)) {
      if (typeof value === 'number') {
        contributions.push({
          feature: key,
          value,
          direction: value > 0 ? 'positive' : 'negative',
        })
      }
    }
  }

  // Sort by absolute value
  contributions.sort((a, b) => Math.abs(b.value) - Math.abs(a.value))

  return {
    positive: contributions.filter((c) => c.direction === 'positive').slice(0, topN),
    negative: contributions.filter((c) => c.direction === 'negative').slice(0, topN),
  }
}

/**
 * Format feature names for human readability.
 */
function formatFeatureName(feature: string): string {
  return (
    feature
      .replace(/_/g, ' ')
      .replace(/([a-z])([A-Z])/g, '$1 $2')
      .toLowerCase()
      .replace(/^\w/, (c) => c.toUpperCase()) || feature
  )
}

/**
 * Create a friendly description of a single SHAP contribution.
 */
export function describeSHAPContribution(
  feature: string,
  value: number,
  direction: 'positive' | 'negative'
): string {
  const prettifiedFeature = formatFeatureName(feature)
  const magnitude = Math.abs(value).toFixed(3)
  const action = direction === 'positive' ? 'increases' : 'decreases'

  return `${prettifiedFeature} ${action} the score by ${magnitude}`
}

/**
 * Get color for a SHAP contribution based on direction.
 */
export function getShapColor(direction: 'positive' | 'negative'): string {
  return direction === 'positive' ? '#10b981' : '#ef4444'
}

/**
 * Format SHAP value for display with sign.
 */
export function formatShapValue(value: number): string {
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(4)}`
}
