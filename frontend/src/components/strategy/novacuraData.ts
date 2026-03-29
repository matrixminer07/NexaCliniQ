export type ScoreTone = 'green' | 'yellow' | 'red'

export interface StrategyMetricRow {
  metric: string
  strategyA: { label: string; score: number; tone: ScoreTone }
  strategyB: { label: string; score: number; tone: ScoreTone }
  strategyC: { label: string; score: number; tone: ScoreTone }
}

export const strategyHeaders = {
  a: 'Strategy A: AI-First Drug Discovery',
  b: 'Strategy B: Traditional + AI Assist',
  c: 'Strategy C: Licensing/Partnership-Only',
}

export const strategyMetricRows: StrategyMetricRow[] = [
  {
    metric: 'Cost',
    strategyA: { label: '₹230M', score: 8.7, tone: 'green' },
    strategyB: { label: '₹360M', score: 6.4, tone: 'yellow' },
    strategyC: { label: '₹120M', score: 7.1, tone: 'yellow' },
  },
  {
    metric: 'Timeline',
    strategyA: { label: '5 years', score: 8.5, tone: 'green' },
    strategyB: { label: '7+ years', score: 5.4, tone: 'red' },
    strategyC: { label: '3-4 years', score: 7.6, tone: 'green' },
  },
  {
    metric: 'Risk Level',
    strategyA: { label: 'Moderate', score: 7.3, tone: 'yellow' },
    strategyB: { label: 'High', score: 5.6, tone: 'red' },
    strategyC: { label: 'Moderate', score: 7.0, tone: 'yellow' },
  },
  {
    metric: 'Scientific Feasibility',
    strategyA: { label: 'High', score: 8.9, tone: 'green' },
    strategyB: { label: 'Medium', score: 6.9, tone: 'yellow' },
    strategyC: { label: 'Low direct control', score: 5.8, tone: 'red' },
  },
  {
    metric: 'Market Potential',
    strategyA: { label: 'Breakout upside', score: 9.1, tone: 'green' },
    strategyB: { label: 'Steady', score: 6.8, tone: 'yellow' },
    strategyC: { label: 'Capped upside', score: 6.2, tone: 'yellow' },
  },
  {
    metric: 'Regulatory Complexity',
    strategyA: { label: 'Manageable', score: 7.8, tone: 'green' },
    strategyB: { label: 'Complex', score: 6.0, tone: 'yellow' },
    strategyC: { label: 'Low direct burden', score: 8.1, tone: 'green' },
  },
  {
    metric: 'Recommended?',
    strategyA: { label: 'Winner', score: 9.2, tone: 'green' },
    strategyB: { label: 'Secondary fallback', score: 6.0, tone: 'yellow' },
    strategyC: { label: 'Portfolio complement', score: 6.5, tone: 'yellow' },
  },
]

export interface RoiInputs {
  strategyA: number
  strategyB: number
  strategyC: number
  marketMultiplier: number
  safetyMultiplier: number
  speedMultiplier: number
}

export interface RoiYearPoint {
  year: string
  strategyA: number
  strategyB: number
  strategyC: number
  total: number
}

export interface RoiOutput {
  points: RoiYearPoint[]
  totalInvested: number
  projectedFiveYearReturn: number
  irrEstimate: number
}

const yearCurve = [0.08, 0.18, 0.22, 0.24, 0.28]

export const defaultRoiInputs: RoiInputs = {
  strategyA: 250,
  strategyB: 150,
  strategyC: 100,
  marketMultiplier: 0.18,
  safetyMultiplier: 0.11,
  speedMultiplier: 0.09,
}

export function roiCalculator(inputs: RoiInputs): RoiOutput {
  const totalA = inputs.strategyA * 4.2 * (1 + inputs.marketMultiplier)
  const totalB = inputs.strategyB * 2.1 * (1 + inputs.safetyMultiplier)
  const totalC = inputs.strategyC * 1.4 * (1 + inputs.speedMultiplier)

  let accA = 0
  let accB = 0
  let accC = 0

  const points = yearCurve.map((weight, idx) => {
    accA += totalA * weight
    accB += totalB * weight
    accC += totalC * weight
    const total = accA + accB + accC
    return {
      year: `Y${idx + 1}`,
      strategyA: Number(accA.toFixed(1)),
      strategyB: Number(accB.toFixed(1)),
      strategyC: Number(accC.toFixed(1)),
      total: Number(total.toFixed(1)),
    }
  })

  const invested = inputs.strategyA + inputs.strategyB + inputs.strategyC
  const fiveYear = points[points.length - 1]?.total ?? 0
  const irr = invested > 0 ? Math.pow(fiveYear / invested, 1 / 5) - 1 : 0

  return {
    points,
    totalInvested: Number(invested.toFixed(1)),
    projectedFiveYearReturn: Number(fiveYear.toFixed(1)),
    irrEstimate: Number((irr * 100).toFixed(2)),
  }
}

export interface GanttMilestone {
  id: string
  label: string
  yearStart: number
  yearEnd: number
  phase: 'Research' | 'Clinical' | 'Commercial'
  detail: string
}

export const ganttMilestones: GanttMilestone[] = [
  { id: 'm1', label: 'Platform Build', yearStart: 1.0, yearEnd: 1.7, phase: 'Research', detail: 'Core platform build, team hiring, IND filing prep.' },
  { id: 'm2', label: 'IND + Phase 1 Start', yearStart: 2.0, yearEnd: 2.8, phase: 'Clinical', detail: 'IND approval, Phase 1 start, two AI candidates identified.' },
  { id: 'm3', label: 'Phase 1 Complete', yearStart: 3.0, yearEnd: 3.8, phase: 'Clinical', detail: 'Phase 1 completion, Phase 2 start, Series B raise.' },
  { id: 'm4', label: 'Phase 2 Readout', yearStart: 4.0, yearEnd: 4.8, phase: 'Clinical', detail: 'Phase 2 readout, NDA prep, partnership deals.' },
  { id: 'm5', label: 'NDA + Launch Prep', yearStart: 5.0, yearEnd: 5.7, phase: 'Commercial', detail: 'NDA submission, launch prep, first licensing revenue.' },
]

export const phaseColors: Record<GanttMilestone['phase'], string> = {
  Research: '#3b82f6',
  Clinical: '#f59e0b',
  Commercial: '#22c55e',
}

export type PipelineStatus = 'completed' | 'active' | 'projected'

export interface RegulatoryStage {
  label: string
  date: string
  status: PipelineStatus
}

export interface RegulatoryStrategy {
  name: string
  stages: RegulatoryStage[]
}

export const regulatoryPipelines: RegulatoryStrategy[] = [
  {
    name: 'Strategy A',
    stages: [
      { label: 'IND', date: 'Q2 Y1', status: 'completed' },
      { label: 'Ph1', date: 'Q1 Y2', status: 'completed' },
      { label: 'Ph2', date: 'Q3 Y3', status: 'active' },
      { label: 'Ph3', date: 'Q1 Y5', status: 'projected' },
      { label: 'NDA', date: 'Q4 Y5', status: 'projected' },
    ],
  },
  {
    name: 'Strategy B',
    stages: [
      { label: 'IND', date: 'Q4 Y1', status: 'completed' },
      { label: 'Ph1', date: 'Q3 Y2', status: 'active' },
      { label: 'Ph2', date: 'Q2 Y4', status: 'projected' },
      { label: 'Ph3', date: 'Pending', status: 'projected' },
      { label: 'NDA', date: 'Y7+', status: 'projected' },
    ],
  },
  {
    name: 'Strategy C',
    stages: [
      { label: 'Partner IND', date: 'Varies', status: 'active' },
      { label: 'Gate 1', date: 'Milestone', status: 'projected' },
      { label: 'Gate 2', date: 'Milestone', status: 'projected' },
      { label: 'Gate 3', date: 'Milestone', status: 'projected' },
      { label: 'Direct NDA', date: 'No path', status: 'projected' },
    ],
  },
]

export type PartnerType = 'AI/Tech' | 'CRO' | 'Pharma' | 'Data'

export interface PartnerItem {
  name: string
  type: PartnerType
  relevanceScore: number
  strategyFit: 'A' | 'B' | 'C'
}

export const partners: PartnerItem[] = [
  { name: 'Nvidia', type: 'AI/Tech', relevanceScore: 9.4, strategyFit: 'A' },
  { name: 'Illumina', type: 'Data', relevanceScore: 8.8, strategyFit: 'A' },
  { name: 'Recursion Pharma', type: 'AI/Tech', relevanceScore: 8.6, strategyFit: 'A' },
  { name: 'ICON plc', type: 'CRO', relevanceScore: 8.2, strategyFit: 'B' },
  { name: 'Covance', type: 'CRO', relevanceScore: 7.9, strategyFit: 'B' },
  { name: 'BMS', type: 'Pharma', relevanceScore: 8.4, strategyFit: 'C' },
  { name: 'Tempus AI', type: 'Data', relevanceScore: 8.7, strategyFit: 'A' },
]

export interface MarketBubble {
  name: string
  maturity: number
  aiIntegration: number
  marketCap: number
  keyDrug: string
  aiApproach: string
  area: 'Oncology' | 'Rare Disease' | 'CNS' | 'Platform'
}

export const marketBubbles: MarketBubble[] = [
  { name: 'Recursion', maturity: 7.8, aiIntegration: 9.2, marketCap: 2300, keyDrug: 'REC-994', aiApproach: 'phenomics + ML', area: 'Platform' },
  { name: 'Schrodinger', maturity: 8.1, aiIntegration: 8.8, marketCap: 2600, keyDrug: 'SGR-1505', aiApproach: 'physics + AI design', area: 'Oncology' },
  { name: 'Insilico Medicine', maturity: 7.1, aiIntegration: 9.4, marketCap: 1500, keyDrug: 'INS018_055', aiApproach: 'gen-AI chemistry', area: 'Rare Disease' },
  { name: 'BenevolentAI', maturity: 6.6, aiIntegration: 8.4, marketCap: 700, keyDrug: 'BEN-2293', aiApproach: 'knowledge graph AI', area: 'CNS' },
  { name: 'Exscientia', maturity: 7.4, aiIntegration: 8.9, marketCap: 1200, keyDrug: 'EXS-21546', aiApproach: 'precision design AI', area: 'Oncology' },
  { name: 'Relay Therapeutics', maturity: 8.0, aiIntegration: 7.8, marketCap: 1800, keyDrug: 'RLY-2608', aiApproach: 'structural dynamics AI', area: 'Oncology' },
  { name: 'AbSci', maturity: 5.8, aiIntegration: 8.6, marketCap: 500, keyDrug: 'ABS-101', aiApproach: 'antibody foundation model', area: 'Platform' },
  { name: 'NexaClinIQ', maturity: 6.2, aiIntegration: 9.6, marketCap: 500, keyDrug: 'NC-201', aiApproach: 'multi-modal oncology AI', area: 'Oncology' },
]

export const marketAreaColors: Record<MarketBubble['area'], string> = {
  Oncology: '#22c55e',
  'Rare Disease': '#f59e0b',
  CNS: '#ef4444',
  Platform: '#3b82f6',
}
