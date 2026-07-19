import { create } from "zustand";
import type { AnalysisRun, Review } from "../api/types";

interface AnalysisStore {
  runs: AnalysisRun[];
  selectedRun: AnalysisRun | null;
  reviews: Review[];
  isLoading: boolean;
  error: string | null;

  setRuns: (runs: AnalysisRun[]) => void;
  setSelectedRun: (run: AnalysisRun | null) => void;
  setReviews: (reviews: Review[]) => void;
  setIsLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  fetchRuns: () => Promise<void>;
  fetchRunById: (id: number) => Promise<void>;
  fetchReviewsByRunId: (id: number) => Promise<void>;
}

export const useAnalysisStore = create<AnalysisStore>((set, get) => ({
  runs: [],
  selectedRun: null,
  reviews: [],
  isLoading: false,
  error: null,

  setRuns: (runs) => set({ runs }),
  setSelectedRun: (run) => set({ selectedRun: run }),
  setReviews: (reviews) => set({ reviews }),
  setIsLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),

  fetchRuns: async () => {
    try {
      set({ isLoading: true, error: null });
      const { apiClient } = await import("../api/client");
      const runs = await apiClient.getRuns();
      set({ runs, isLoading: false });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
    }
  },

  fetchRunById: async (id) => {
    try {
      set({ isLoading: true, error: null });
      const { apiClient } = await import("../api/client");
      const run = await apiClient.getRunById(id);
      set({ selectedRun: run, isLoading: false });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
    }
  },

  fetchReviewsByRunId: async (id) => {
    try {
      set({ isLoading: true, error: null });
      const { apiClient } = await import("../api/client");
      const reviews = await apiClient.getReviewsByRunId(id);
      set({ reviews, isLoading: false });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
    }
  },
}));
