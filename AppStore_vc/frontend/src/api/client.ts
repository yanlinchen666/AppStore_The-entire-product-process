import type {
  AnalysisRun,
  AnalyzeRequest,
  AnalyzeResponse,
  EvidenceSearchRequest,
  EvidenceSearchResult,
  EvidenceValidateRequest,
  EvidenceValidateResponse,
  Finding,
  Requirement,
  Review,
  TestCase,
  TraceabilityChain,
  ProgressResponse,
} from "./types";

const BASE_URL = "/api";

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
    const data = await response.json();
    return data.run;
  },

  getReviewsByRunId: async (id: number): Promise<Review[]> => {
    const response = await fetch(`${BASE_URL}/runs/${id}/reviews`);
    if (!response.ok) {
      throw new Error("Failed to fetch reviews");
    }
    return response.json();
  },

  getFindingsByRunId: async (id: number): Promise<Finding[]> => {
    const response = await fetch(`${BASE_URL}/runs/${id}/findings`);
    if (!response.ok) {
      throw new Error("Failed to fetch findings");
    }
    return response.json();
  },

  getRequirementsByRunId: async (id: number): Promise<Requirement[]> => {
    const response = await fetch(`${BASE_URL}/runs/${id}/requirements`);
    if (!response.ok) {
      throw new Error("Failed to fetch requirements");
    }
    return response.json();
  },

  getTestCasesByRunId: async (id: number): Promise<TestCase[]> => {
    const response = await fetch(`${BASE_URL}/runs/${id}/testcases`);
    if (!response.ok) {
      throw new Error("Failed to fetch test cases");
    }
    return response.json();
  },

  getTraceabilityChain: async (id: number): Promise<TraceabilityChain> => {
    const response = await fetch(`${BASE_URL}/runs/${id}/traceability`);
    if (!response.ok) {
      throw new Error("Failed to fetch traceability chain");
    }
    return response.json();
  },

  analyze: async (data: AnalyzeRequest): Promise<AnalyzeResponse> => {
    const response = await fetch(`${BASE_URL}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to start analysis");
    }
    return response.json();
  },

  getAnalysisProgress: async (runId: number): Promise<ProgressResponse> => {
    const response = await fetch(`${BASE_URL}/analyze/${runId}/progress`);
    if (!response.ok) {
      throw new Error("Failed to fetch progress");
    }
    return response.json();
  },

  importReviews: async (file: File, format: string, appId?: string): Promise<{
    status: string;
    reviews_imported: number;
    app_id: string;
    app_name: string;
  }> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("format", format);
    if (appId) {
      formData.append("app_id", appId);
    }
    const response = await fetch(`${BASE_URL}/import`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to import reviews");
    }
    return response.json();
  },

  analyzeImported: async (appId: string, appName: string, analysisGoal: string): Promise<AnalyzeResponse> => {
    const params = new URLSearchParams({
      app_id: appId,
      app_name: appName,
      analysis_goal: analysisGoal,
    });
    const response = await fetch(`${BASE_URL}/import/analyze?${params}`, {
      method: "POST",
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Failed to start analysis on imported data");
    }
    return response.json();
  },

  searchEvidence: async (data: EvidenceSearchRequest): Promise<{ query: string; results: EvidenceSearchResult[] }> => {
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error("Failed to validate evidence");
    }
    return response.json();
  },
};
