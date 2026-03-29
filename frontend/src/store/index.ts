import { create } from 'zustand'
import type { FeatureSet, PredictionResponse, TabKey, TherapeuticArea, CounterfactualResponse } from '@/types'

export const defaultFeatures: FeatureSet = {
  toxicity: 0.3,
  bioavailability: 0.7,
  solubility: 0.6,
  binding: 0.8,
  molecular_weight: 0.5,
}

interface AppState {
  currentTab: TabKey
  setCurrentTab: (tab: TabKey) => void
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
  compoundName: string
  setCompoundName: (name: string) => void
  smiles: string
  setSmiles: (smiles: string) => void
  therapeuticArea: TherapeuticArea
  setTherapeuticArea: (ta: TherapeuticArea) => void
  targetProbability: number
  setTargetProbability: (value: number) => void
  featuresA: FeatureSet
  featuresB: FeatureSet
  setFeatureA: (key: keyof FeatureSet, value: number) => void
  setFeatureB: (key: keyof FeatureSet, value: number) => void
  resetA: () => void
  prediction: PredictionResponse | null
  setPrediction: (prediction: PredictionResponse | null) => void
  counterfactual: CounterfactualResponse | null
  setCounterfactual: (counterfactual: CounterfactualResponse | null) => void
  totalAnalysed: number
  passRate: number
  yearsSaved: number
  setLiveMetrics: (values: { totalAnalysed: number; passRate: number; yearsSaved: number }) => void
}

export const useAppStore = create<AppState>((set) => ({
  currentTab: 'compare',
  setCurrentTab: (tab) => set({ currentTab: tab }),
  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  compoundName: 'Compound A',
  setCompoundName: (name) => set({ compoundName: name }),
  smiles: '',
  setSmiles: (smiles) => set({ smiles }),
  therapeuticArea: 'oncology',
  setTherapeuticArea: (ta) => set({ therapeuticArea: ta }),
  targetProbability: 0.75,
  setTargetProbability: (value) => set({ targetProbability: value }),
  featuresA: defaultFeatures,
  featuresB: { ...defaultFeatures, toxicity: 0.45, binding: 0.65 },
  setFeatureA: (key, value) => set((state) => ({ featuresA: { ...state.featuresA, [key]: value } })),
  setFeatureB: (key, value) => set((state) => ({ featuresB: { ...state.featuresB, [key]: value } })),
  resetA: () => set({ featuresA: defaultFeatures, prediction: null, counterfactual: null }),
  prediction: null,
  setPrediction: (prediction) => set({ prediction }),
  counterfactual: null,
  setCounterfactual: (counterfactual) => set({ counterfactual }),
  totalAnalysed: 847,
  passRate: 31,
  yearsSaved: 3.4,
  setLiveMetrics: (values) => set(values),
}))

