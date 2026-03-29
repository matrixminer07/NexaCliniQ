// src/types/prediction.types.ts

export interface PredictionInputs {
  toxicity: number;
  bioavailability: number;
  solubility: number;
  binding: number;
  molecular_weight: number;
}

export interface PhaseProbs {
  phase1: number;
  phase2: number;
  phase3: number;
  overall_pos: number;
  uplift_vs_baseline: number;
}

export interface ConfidenceInterval {
  p10: number; p50: number; p90: number; std: number;
}

export interface SHAPValues {
  toxicity: number;
  bioavailability: number;
  solubility: number;
  binding: number;
  molecular_weight: number;
}

export interface PredictionResult {
  success_probability: number;
  confidence_interval: ConfidenceInterval;
  shap_values?: SHAPValues;
  shap_breakdown?: {
    contributions?: Array<{
      feature: string;
      value: number;
      shap: number;
      direction?: string;
    }>;
    top_driver?: string;
    top_direction?: string;
  };
  phase_probabilities: PhaseProbs;
  warnings: string[];
}
