export const GLOSSARY: Record<string, { term: string; definition: string; learnMore?: string }> = {
  SHAP: {
    term: 'SHAP value',
    definition:
      'SHapley Additive exPlanations — measures how much each feature contributed to this specific prediction, relative to the baseline.',
    learnMore: 'https://shap.readthedocs.io',
  },
  phase_pos: {
    term: 'Phase probability of success',
    definition:
      'The estimated likelihood this compound survives each clinical trial phase, based on historical success rates for similar compounds.',
  },
  ci_width: {
    term: 'Confidence interval width',
    definition:
      'A narrow CI (< 0.1) means the model is certain. A wide CI (> 0.3) indicates high uncertainty — treat predictions cautiously.',
  },
  hERG: {
    term: 'hERG liability',
    definition:
      'Human Ether-à-go-go Related Gene channel inhibition — a common cause of drug-induced cardiac toxicity. High hERG binding is a major safety flag.',
  },
  lipinski: {
    term: "Lipinski's Rule of Five",
    definition:
      'A set of molecular property thresholds predicting oral bioavailability. Violations do not disqualify a compound but increase development risk.',
  },
  admet: {
    term: 'ADMET properties',
    definition:
      'Absorption, Distribution, Metabolism, Excretion, and Toxicity — key pharmacokinetic and safety indicators for drug candidates.',
  },
  toxicity: {
    term: 'Toxicity score',
    definition: 'Predicted likelihood of adverse or toxic effects. Higher values indicate greater safety risk.',
  },
  bioavailability: {
    term: 'Bioavailability',
    definition:
      'The fraction of an administered dose that reaches systemic circulation. Higher values indicate better oral absorption.',
  },
  solubility: {
    term: 'Solubility',
    definition:
      'How well the compound dissolves in water or biological fluids. Poor solubility can limit absorption and efficacy.',
  },
  binding: {
    term: 'Target binding affinity',
    definition:
      'How strongly the compound binds to the intended therapeutic target. Higher binding typically improves efficacy.',
  },
  molecular_weight: {
    term: 'Molecular weight',
    definition:
      'The mass of the compound. Very high MW (> 500 Da) or very low MW can affect drug-like properties.',
  },
  verdictPass: {
    term: 'Verdict: PASS',
    definition:
      'Compound shows favorable properties across key indicators and is recommended for advancement into development.',
  },
  verdictCaution: {
    term: 'Verdict: CAUTION',
    definition:
      'Compound has mixed signals — some favorable properties but notable concerns that require mitigation or further testing.',
  },
  verdictFail: {
    term: 'Verdict: FAIL',
    definition:
      'Compound shows significant liabilities that would typically exclude it from advancement without substantial chemical modification.',
  },
  npv: {
    term: 'Net Present Value (NPV)',
    definition:
      'The sum of all discounted future cash flows. A positive NPV indicates the project is expected to create value.',
  },
  irr: {
    term: 'Internal Rate of Return (IRR)',
    definition:
      'The discount rate at which NPV equals zero. A higher IRR indicates a more attractive investment.',
  },
  sensitivityAnalysis: {
    term: 'Sensitivity analysis',
    definition:
      'Tests how changes in key assumptions (e.g., success rates, costs) impact financial outcomes.',
  },
  monteCarloSimulation: {
    term: 'Monte Carlo simulation',
    definition:
      'Uses probabilistic models to generate a range of outcomes and their likelihoods, accounting for uncertainty.',
  },
}
