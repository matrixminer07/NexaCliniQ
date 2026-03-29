import { create } from "zustand";

interface FinancialState {
  budget: {
    ai: number;
    clinical: number;
    ma: number;
    ops: number;
    reg: number;
  };
  setBudget: (budget: Partial<FinancialState["budget"]>) => void;
  npvResults: any;
  setNpvResults: (results: any) => void;
  monteCarloData: any[]; // Streamed batches of distribution data
  setMonteCarloData: (data: any[]) => void;
  clearMonteCarloData: () => void;
  sensitivityData: any;
  setSensitivityData: (data: any) => void;
}

export const useFinancialStore = create<FinancialState>((set) => ({
  budget: {
    ai: 180,
    clinical: 150,
    ma: 90,
    ops: 50,
    reg: 30,
  },
  setBudget: (budget) => set((s) => ({ budget: { ...s.budget, ...budget } })),
  npvResults: null,
  setNpvResults: (npvResults) => set({ npvResults }),
  monteCarloData: [],
  setMonteCarloData: (newBatch) => set((s) => ({ monteCarloData: [...s.monteCarloData, ...newBatch] })),
  clearMonteCarloData: () => set({ monteCarloData: [] }),
  sensitivityData: null,
  setSensitivityData: (sensitivityData) => set({ sensitivityData })
}));
