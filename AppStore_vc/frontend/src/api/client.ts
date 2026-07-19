import type {
  AnalysisRun,
  AnalyzeRequest,
  AnalyzeResponse,
  EvidenceSearchRequest,
  EvidenceSearchResult,
  EvidenceValidateRequest,
  EvidenceValidateResponse,
  Review,
  TraceabilityChain,
} from "./types";

const BASE_URL = "http://localhost:8000/api";

export const apiClient = {
  getRuns: async (): Promise<AnalysisRun[]> => {
    const response = await fetch(`${BASE_URL}/runs`);
    if (!response.ok) {
      throw new Error("Failed to fetch runs");
    }
    return response.json();
  },

  getRunById: async (id: number): Promise<AnalysisRun> => {
    const response = await fetch(`${BASE_URL}/runs/${id}`);
    if (!response.ok) {
      throw new Error("Failed to fetch run");
    }
    return response.json();
  },

  getReviewsByRunId: async (id: number): Promise<Review[]> => {
    const response = await fetch(`${BASE_URL}/runs/${id}/reviews`);
    if (!response.ok) {
      throw new Error("Failed to fetch reviews");
    }
    return response.json();
  },

  getTraceabilityChain: async (id: number): Promise<TraceabilityChain[]> => {
    const response = await fetch(`${BASE_URL}/runs/${id}/traceability`);
    if (!response.ok) {
      throw new Error("Failed to fetch traceability chain");
    }
    return response.json();
  },

  analyze: async (data: AnalyzeRequest): Promise<AnalyzeResponse> => {
    const response = await fetch(`${BASE_URL}/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error("Failed to start analysis");
    }
    return response.json();
  },

  searchEvidence: async (data: EvidenceSearchRequest): Promise<EvidenceSearchResult[]> => {
    const params = new URLSearchParams({
      query: data.query,
      ...(data.top_k && { top_k: data.top_k.toString() }),
    });
    const response = await fetch(`${BASE_URL}/evidence/search?${params}`);
    if (!response.ok) {
      throw new Error("Failed to search evidence");
    }
    return response.json();
  },

  validateEvidence: async (data: EvidenceValidateRequest): Promise<EvidenceValidateResponse> => {
    const response = await fetch(`${BASE_URL}/evidence/validate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error("Failed to validate evidence");
    }
    return response.json();
  },
};
