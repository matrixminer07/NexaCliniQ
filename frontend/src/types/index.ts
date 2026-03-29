export type VerdictLabel = 'PASS' | 'CAUTION' | 'FAIL'

export type TabKey =
  | 'predict'
  | 'compare'
  | 'strategy'
  | 'market-sizing'
  | 'risk-register'
  | 'financial-detail'
  | 'executive-summary'
  | 'competition'
  | 'regulatory'
  | 'partnerships'
  | 'roadmap'
  | 'pipeline'
  | 'history'
  | 'scenarios'
  | 'financial'

export type TherapeuticArea = 'oncology' | 'cns' | 'rare' | 'cardiology' | 'infectious' | 'metabolic'

export interface FeatureSet {
  toxicity: number
  bioavailability: number
  solubility: number
  binding: number
  molecular_weight: number
}

export interface Verdict {
  verdict: VerdictLabel
  color: string
  score: number
}

export interface ConfidenceBand {
  p10: number
  p50: number
  p90: number
  std: number
}

export interface ShapContribution {
  feature: keyof FeatureSet
  value: number
  shap: number
  direction: 'positive' | 'negative'
}

export interface ShapBreakdown {
  base_value: number
  final_prediction: number
  contributions: ShapContribution[]
  top_driver: string
  top_direction: 'positive' | 'negative'
}

export interface AdmetProfile {
  mw_daltons: number
  logp_estimate: number
  tpsa_estimate?: number
  bbb_likely?: boolean
  herg_risk: boolean
  lipinski_pass: boolean
  drug_likeness: string
  drug_likeness_score?: number
  admet_warnings?: string[]
}

export interface PredictionResponse {
  success_probability: number
  verdict: Verdict
  confidence_interval: ConfidenceBand
  shap_breakdown: ShapBreakdown
  phase_probabilities: Record<string, number>
  admet: AdmetProfile
  warnings: string[]
}

export interface CounterfactualChange {
  feature: keyof FeatureSet
  current: number
  suggested: number
  delta: number
  direction: 'increase' | 'decrease'
}

export interface CounterfactualResponse {
  reachable?: boolean
  already_above_target?: boolean
  target_prob?: number
  achieved_prob?: number
  changes_required?: CounterfactualChange[]
  recommendation?: string
}

export interface InsightCard {
  kind: 'strength' | 'opportunity' | 'next'
  title: string
  text: string
}

export interface HistoryRecord extends FeatureSet {
  id: string
  timestamp: string
  probability: number
  verdict: VerdictLabel
  warnings: string[]
  tags: string[]
  notes: string
  compound_name: string
  shap_breakdown?: ShapBreakdown | null
}

export interface ActiveLearningItem {
  id: string
  compound_name: string
  uncertainty_score: number
  predicted_prob: number
  priority: string
  status: string
}

export interface Scenario {
  id: string
  name: string
  inputs: Partial<FeatureSet>
  outputs?: Record<string, unknown>
  tags?: string[]
  created_at?: string
}

export interface StrategyOption {
  id: string
  name: string
  summary: string
  timeline_years: number
  capex_musd: number
  expected_npv_musd: number
  scientific_opportunity: string
  execution_risk: string
  regulatory_risk: string
  talent_complexity: string
  score: {
    scientific_feasibility: number
    financial_sustainability: number
    market_competitiveness: number
    healthcare_impact: number
  }
  key_risks: string[]
}

export interface StrategyOptionsResponse {
  recommended: string
  recommendation_summary: string
  options: StrategyOption[]
}

export interface MarketSizingSegment {
  segment: string
  sam_busd: number
  share_pct: number
  growth_pct: number
  priority: 'High' | 'Medium' | 'Low'
  rationale: string
}

export interface MarketSizingAssumption {
  name: string
  value: string
  sensitivity: 'High' | 'Medium' | 'Low'
}

export interface MarketSizingResponse {
  as_of: string
  currency: string
  market: {
    tam_busd: number
    sam_busd: number
    som_busd: number
    cagr_pct: number
    horizon_year: number
  }
  segments: MarketSizingSegment[]
  assumptions: MarketSizingAssumption[]
}

export interface RiskRegisterItem {
  id: string
  title: string
  category: 'Data' | 'Regulatory' | 'Execution' | 'Financial' | 'Partnership'
  option_id: string
  probability: number
  impact: number
  score: number
  owner: string
  mitigation: string
  status: 'Open' | 'Mitigating' | 'Monitored' | 'Closed'
  due_quarter: string
}

export interface RiskRegisterResponse {
  updated_at: string
  items: RiskRegisterItem[]
}

export interface CompetitivePlayer {
  name: string
  region: string
  platform: number
  translation: number
  focus: string
}

export interface CompetitiveLandscape {
  positioning_axes: {
    x: string
    y: string
  }
  players: CompetitivePlayer[]
  regional_signal: Array<{ region: string; summary: string }>
}

export interface RegulatoryMilestone {
  year: number
  agency: string
  milestone: string
  impact: string
}

export interface PartnershipItem {
  name: string
  type: string
  rationale: string
  priority: string
}

export interface RoadmapPhase {
  phase: string
  window: string
  focus: string
  outcomes: string[]
}

export interface FeatureTrackerCategory {
  key: string
  label: string
  items: string[]
}

export interface FeatureTrackerData {
  summary: {
    total: number
    frontend: number
    backend: number
    ml_data: number
  }
  categories: FeatureTrackerCategory[]
}
