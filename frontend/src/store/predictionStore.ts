// src/store/predictionStore.ts
import { create } from "zustand";
import type { PredictionResult } from "../types/prediction.types";

interface PredictionState {
  inputs: {
    toxicity: number;
    bioavailability: number;
    solubility: number;
    binding: number;
    molecular_weight: number;
  };
  result: PredictionResult | null;
  loading: boolean;
  setInputs: (inputs: Partial<PredictionState["inputs"]>) => void;
  setResult: (result: PredictionResult) => void;
  setLoading: (v: boolean) => void;
}

export const usePredictionStore = create<PredictionState>((set) => ({
  inputs: {
    toxicity: 0.3,
    bioavailability: 0.7,
    solubility: 0.6,
    binding: 0.8,
    molecular_weight: 0.5,
  },
  result: null,
  loading: false,
  setInputs: (inputs) => set((s) => ({ inputs: { ...s.inputs, ...inputs } })),
  setResult: (result) => set({ result }),
  setLoading: (loading) => set({ loading }),
}));
