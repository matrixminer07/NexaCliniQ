import type { AdmetProfile, FeatureSet, PredictionResponse, ShapBreakdown, VerdictLabel } from '@/types'

function clamp(value: number, min = 0, max = 1): number {
  return Math.min(max, Math.max(min, value))
}

function getVerdict(probability: number): VerdictLabel {
  if (probability >= 0.7) return 'PASS'
  if (probability >= 0.4) return 'CAUTION'
  return 'FAIL'
}

function getVerdictColor(probability: number): string {
  if (probability >= 0.7) return '#16A34A'
  if (probability >= 0.4) return '#D97706'
  return '#DC2626'
}

function buildConfidenceInterval(probability: number) {
  const spread = clamp(0.08 + (1 - probability) * 0.06, 0.05, 0.14)
  return {
    p10: clamp(probability - spread),
    p50: probability,
    p90: clamp(probability + spread),
    std: Number((spread / 1.28).toFixed(3)),
  }
}

function buildShapBreakdown(features: FeatureSet, probability: number): ShapBreakdown {
  const contributions = [
    {
      feature: 'toxicity' as const,
      value: features.toxicity,
      shap: Number((-0.4 * features.toxicity).toFixed(3)),
      direction: 'negative' as const,
    },
    {
      feature: 'bioavailability' as const,
      value: features.bioavailability,
      shap: Number((0.3 * features.bioavailability).toFixed(3)),
      direction: 'positive' as const,
    },
    {
      feature: 'solubility' as const,
      value: features.solubility,
      shap: Number((0.2 * features.solubility).toFixed(3)),
      direction: 'positive' as const,
    },
    {
      feature: 'binding' as const,
      value: features.binding,
      shap: Number((0.3 * features.binding).toFixed(3)),
      direction: 'positive' as const,
    },
    {
      feature: 'molecular_weight' as const,
      value: features.molecular_weight,
      shap: Number((0.05 * (features.molecular_weight - 0.5)).toFixed(3)),
      direction: features.molecular_weight >= 0.5 ? ('positive' as const) : ('negative' as const),
    },
  ]

  const topContributor = contributions.reduce((best, current) => {
    if (!best) return current
    return Math.abs(current.shap) > Math.abs(best.shap) ? current : best
  }, contributions[0])

  return {
    base_value: 0.35,
    final_prediction: probability,
    contributions,
    top_driver: topContributor.feature.replace(/_/g, ' '),
    top_direction: topContributor.direction,
  }
}

function buildAdmetProfile(features: FeatureSet, probability: number): AdmetProfile {
  const mwDaltons = 150 + features.molecular_weight * 450
  const logpEstimate = Number((features.binding * 2 - features.toxicity * 1.5 + 0.5).toFixed(2))
  const lipinskiPass = mwDaltons < 500 && features.solubility >= 0.25
  const hergRisk = features.toxicity > 0.7 || probability < 0.35

  return {
    mw_daltons: Number(mwDaltons.toFixed(1)),
    logp_estimate: logpEstimate,
    tpsa_estimate: Number((40 + (1 - features.solubility) * 80).toFixed(1)),
    bbb_likely: features.bioavailability >= 0.55 && features.toxicity < 0.6,
    herg_risk: hergRisk,
    lipinski_pass: lipinskiPass,
    drug_likeness: probability >= 0.7 ? 'High' : probability >= 0.4 ? 'Moderate' : 'Low',
    drug_likeness_score: Number((probability * 10).toFixed(1)),
    admet_warnings: [
      ...(features.toxicity > 0.7 ? ['High toxicity risk detected'] : []),
      ...(features.bioavailability < 0.4 ? ['Low bioavailability risk detected'] : []),
      ...(features.solubility < 0.35 ? ['Low solubility may limit exposure'] : []),
    ],
  }
}

export function buildLocalPredictionResponse(features: FeatureSet & { compound_name?: string }): PredictionResponse {
  const rawScore =
    0.05 +
    features.bioavailability * 0.3 +
    features.binding * 0.3 +
    features.solubility * 0.2 -
    features.toxicity * 0.4 +
    features.molecular_weight * 0.05

  const successProbability = clamp(Number(rawScore.toFixed(4)))
  const verdict = getVerdict(successProbability)

  return {
    success_probability: successProbability,
    verdict: {
      verdict,
      color: getVerdictColor(successProbability),
      score: Number((successProbability * 100).toFixed(1)),
    },
    confidence_interval: buildConfidenceInterval(successProbability),
    shap_breakdown: buildShapBreakdown(features, successProbability),
    phase_probabilities: {
      phase1: Number(clamp(successProbability * 0.72 + 0.08).toFixed(3)),
      phase2: Number(clamp(successProbability * 0.6 + 0.05).toFixed(3)),
      phase3: Number(clamp(successProbability * 0.48 + 0.03).toFixed(3)),
      overall_pos: Number((successProbability * 100).toFixed(1)),
    },
    admet: buildAdmetProfile(features, successProbability),
    warnings: [
      ...(features.toxicity > 0.7 ? ['High toxicity risk detected'] : []),
      ...(features.bioavailability < 0.4 ? ['Low bioavailability (absorption) risk'] : []),
      ...(features.solubility < 0.35 ? ['Low solubility may limit formulation options'] : []),
    ],
  }
}